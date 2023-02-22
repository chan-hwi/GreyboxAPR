#!/usr/bin/env python3
import os
import sys
import subprocess
import json
import time
import hashlib
from dataclasses import dataclass
import logging
import random
import numpy as np
from enum import Enum
from typing import List, Dict, Tuple, Set, Union
import uuid
import math
class MSVMode(Enum):
  guided = 1
  original = 2
  seapr = 3
  tbar = 4
  recoder = 5
  genprog = 6

# Parameter Type
class PT(Enum):
  selected = 0
  basic = 1 # basic
  plau = 2  # plausible
  fl = 3    # fault localization
  out = 4   # output difference
  cov = 5   # coverage
  rand = 6  # random
  odist = 7    # output distance
  sigma = 8 # standard deviation of normal distribution
  halflife = 9 # half life of parameters
  k = 10    # increase or decrease beta distribution with k
  alpha = 11 # alpha of beta distribution
  beta = 12 # beta of beta distribution
  epsilon = 13 # epsilon-greedy
  b_dec=14 # decrease of beta distribution
  a_init=15 # init value of a in beta dist
  b_init=16 # init value of b in beta dist
  frequency=17 # frequency of basic patches from total basic patches
  bp_frequency=18 # frequency of basic patches from total searched patches in subtree

class SeAPRMode(Enum):
  FILE=0,
  FUNCTION=1,
  LINE=2,
  SWITCH=3,
  TYPE=4

class PassFail:
  def __init__(self, p: float = 0., f: float = 0.) -> None:
    self.pass_count = p
    self.fail_count = f
  def __fixed_beta__(self,use_fixed_beta,alpha,beta):
    if not use_fixed_beta:
      return 1
    else:
      mode=self.beta_mode(alpha,beta)
      return 0.5*(pow(3.7,mode))+0.2
  def __exp_alpha(self, exp_alpha:bool) -> float:
    if exp_alpha:
      if self.pass_count==0:
        return 1.
      else:
        return min(1024.,self.pass_count)
    else:
      return 1.
  def beta_mode(self, alpha: float, beta: float) -> float:
    if alpha+beta==2.0:
      return 1.0
    return (alpha - 1.0) / (alpha + beta - 2.0)
  def update(self, result: bool, n: float,b_n:float=1.0, exp_alpha: bool = False, use_fixed_beta:bool=False) -> None:
    if result:
      self.pass_count += n * self.__exp_alpha(exp_alpha)
    else:
      self.fail_count += b_n*self.__fixed_beta__(use_fixed_beta,self.pass_count,self.fail_count)
  def update_with_pf(self, other,b_n:float=1.0,use_fixed_beta:bool=False) -> None:
    self.pass_count += other.pass_count
    self.fail_count += other.fail_count*self.__fixed_beta__(use_fixed_beta,self.pass_count,self.fail_count)
  def expect_probability(self,additional_score:float=0) -> float:
    return self.beta_mode(self.pass_count + 1.5+additional_score, self.fail_count + 2.0)
  def select_value(self,a_init:float=1.0,b_init:float=1.0) -> float: # select a value randomly from the beta distribution
    return np.random.beta(self.pass_count + a_init, self.fail_count + b_init)
  def copy(self) -> 'PassFail':
    return PassFail(self.pass_count, self.fail_count)
  @staticmethod
  def normalize(x: List[float]) -> List[float]:
    npx = np.array(x)
    x_max = np.max(npx)
    x_min = np.min(npx)
    x_diff = x_max - x_min
    if (x_diff < 1e-6):
      x_norm = npx - x_min
    else:
      x_norm = (npx - x_min) / x_diff
    return x_norm.tolist()
  @staticmethod
  def softmax(x: List[float]) -> List[float]:
    npx = np.array(x)
    y = np.exp(npx)
    f_x = y / np.sum(y)
    return f_x.tolist()
  @staticmethod
  def argmax(x: List[float]) -> int:
    m = max(x)
    tmp = list()
    for i in range(len(x)):
      if x[i] == m:
        tmp.append(i)
    return np.random.choice(tmp)
    # return np.argmax(x)
  @staticmethod
  def select_value_normal(x: List[float], sigma: float) -> List[float]:
    for i in range(len(x)):
      val = x[i]
      #sigma = 0.1 / 1.96 # max(0.001, val * (1 - val) / 10)
      x[i] = np.random.normal(val, sigma)
    return x
  @staticmethod
  def select_by_probability(probability: List[float]) -> int:   # pf_list: list of PassFail
    # probability=[]
    # probability = list(map(lambda x: x.expect_probability(), pf_list))
    total = 0
    for p in probability:
      if p > 0:
        total += p
    rand = random.random() * total
    for i in range(len(probability)):
      if probability[i] < 0:
        continue
      rand -= probability[i]
      if rand <= 0:
        return i
    return 0
  @staticmethod
  def concave_up_exp(x: float, base: float = math.e) -> float:
    return (np.power(base, x) - 1) / (base - 1)
  @staticmethod
  def concave_up(x: float, base: float = math.e) -> float:
    # unique function
    # return np.exp(1 - (1 / (x + 0.000001)))
    return x * x
    # return np.power(base, x-1)
    # return PassFail.concave_up_exp(x, base)
  @staticmethod
  def concave_down(x: float, base: float = math.e) -> float:
    # return 2 * x - PassFail.concave_up(x)
    # return np.power(base, x-1)
    atzero = PassFail.concave_up(0, base)
    return 2 * ((1 - atzero) * x + atzero) - PassFail.concave_up(x, base)
  @staticmethod
  # fail function
  def log_func(x: float, half: float = 51) -> float:
    # a = half + math.pow(half, 0.5)
    a=half
    # a*=0.5
    if a-x<=0:
      return 0.
    else:
      return max(np.log(a - x) / np.log(a), 0.)


class FileInfo:
  def __init__(self, file_name: str) -> None:
    self.file_name = file_name
    #self.line_info_list: List[LineInfo] = list()
    self.func_info_map: Dict[str, FuncInfo] = dict() # f"{func_name}:{func_line_begin}-{func_line_end}"
    self.pf = PassFail()
    self.critical_pf = PassFail()
    self.positive_pf = PassFail()
    self.output_pf = PassFail()
    self.fl_score=-1
    self.fl_score_list: List[float] = list()
    self.out_dist: float = -1.0
    self.out_dist_map: Dict[int, float] = dict()
    self.update_count: int = 0
    self.total_case_info: int = 0
    self.prophet_score:list=[]
    self.has_init_patch=False
    self.case_update_count: int = 0
    self.score_list: List[float] = list()
    self.class_name: str = ""
    self.children_basic_patches:int=0
    self.children_plausible_patches:int=0
    self.consecutive_fail_count:int=0
    self.consecutive_fail_plausible_count:int=0
    self.patches_by_score:Dict[float,List[TbarCaseInfo]]=dict()
    self.remain_patches_by_score:Dict[float,List[TbarCaseInfo]]=dict()
    self.remain_lines_by_score:Dict[float,List[LineInfo]]=dict()
  def __hash__(self) -> int:
    return hash(self.file_name)
  def __eq__(self, other) -> bool:
    return self.file_name == other.file_name

class FuncInfo:
  def __init__(self, parent: FileInfo, func_name: str, begin: int, end: int) -> None:
    self.parent = parent
    self.func_name = func_name
    self.begin = begin
    self.end = end
    self.id = f"{self.func_name}:{self.begin}-{self.end}"
    #self.line_info_list: List[LineInfo] = list()
    self.line_info_map: Dict[uuid.UUID, LineInfo] = dict()
    self.pf = PassFail()
    self.positive_pf = PassFail()
    self.output_pf = PassFail()
    self.fl_score: float = -1.0
    self.fl_score_list: List[float] = list()
    self.out_dist: float = -1.0
    self.out_dist_map: Dict[int, float] = dict()
    self.update_count: int = 0
    self.total_case_info: int = 0
    self.prophet_score: List[float] = []
    self.has_init_patch=False
    self.case_update_count: int = 0
    self.score_list: List[float] = list()
    self.func_rank: int = -1
    self.children_basic_patches:int=0
    self.children_plausible_patches:int=0
    self.consecutive_fail_count:int=0
    self.consecutive_fail_plausible_count:int=0
    self.patches_by_score:Dict[float,List[TbarCaseInfo]]=dict()
    self.remain_patches_by_score:Dict[float,List[TbarCaseInfo]]=dict()
    self.remain_lines_by_score:Dict[float,List[LineInfo]]=dict()

    self.total_patches_by_score:Dict[float,int]=dict() # Total patches grouped by score
    self.searched_patches_by_score:Dict[float,int]=dict() # Total searched patches grouped by score
    self.same_seapr_pf = PassFail(1, 1)
    self.diff_seapr_pf = PassFail(1, 1)
    self.case_rank_list: List[str] = list()

    # Unified debugging stuffs
    self.ud_spectrum:List[int]=[0,0,0,0]  # [CleanFix, NoisyFix, NoneFix, NegFix]
  def __hash__(self) -> int:
    return hash(self.id)
  def __eq__(self, other) -> bool:
    return self.id == other.id and self.parent.file_name == other.parent.file_name

class LineInfo:
  def __init__(self, parent: FuncInfo, line_number: int) -> None:
    self.uuid = uuid.uuid4()
    self.line_number = line_number
    #self.switch_info_list: List[SwitchInfo] = list()
    self.parent = parent
    self.pf = PassFail()
    self.critical_pf = PassFail()
    self.positive_pf = PassFail()
    self.output_pf = PassFail()
    self.fl_score=0.
    self.out_dist: float = -1.0
    self.out_dist_map: Dict[int, float] = dict()
    self.update_count: int = 0
    self.total_case_info: int = 0
    self.prophet_score:list=[]
    self.type_priority=dict()
    self.has_init_patch=False
    self.case_update_count: int = 0
    self.tbar_type_info_map: Dict[str, TbarTypeInfo] = dict()
    # self.recoder_type_info_map: Dict[str, RecoderTypeInfo] = dict()
    self.line_id = -1
    self.recoder_case_info_map: Dict[int, RecoderCaseInfo] = dict()
    self.score_list: List[float] = list()
    self.children_basic_patches:int=0
    self.children_plausible_patches:int=0
    self.consecutive_fail_count:int=0
    self.consecutive_fail_plausible_count:int=0
    self.patches_by_score:Dict[float,List[TbarCaseInfo]]=dict()
    self.remain_patches_by_score:Dict[float,List[TbarCaseInfo]]=dict()

    # Unified debugging stuffs
    self.ud_spectrum:List[int]=[0,0,0,0]  # [CleanFix, NoisyFix, NoneFix, NegFix]
  def __hash__(self) -> int:
    return hash(self.uuid)
  def __eq__(self, other) -> bool:
    return self.uuid == other.uuid

class TbarTypeInfo:
  def __init__(self, parent: LineInfo, mutation: str) -> None:
    self.parent = parent
    self.mutation = mutation
    self.pf = PassFail()
    self.positive_pf = PassFail()
    self.output_pf = PassFail()
    self.update_count: int = 0
    self.total_case_info: int = 0
    self.case_update_count: int = 0
    self.out_dist: float = -1.0
    self.out_dist_map: Dict[int, float] = dict()
    self.tbar_case_info_map: Dict[str, TbarCaseInfo] = dict()
    self.children_basic_patches:int=0
    self.children_plausible_patches:int=0
    self.consecutive_fail_count:int=0
    self.consecutive_fail_plausible_count:int=0
    self.patches_by_score:Dict[float,List[TbarCaseInfo]]=dict()
    self.remain_patches_by_score:Dict[float,List[TbarCaseInfo]]=dict()
  def __hash__(self) -> int:
    return hash(self.mutation)
  def __eq__(self, other) -> bool:
    return self.mutation == other.mutation and self.parent==other.parent

class TbarCaseInfo:
  def __init__(self, parent: TbarTypeInfo, location: str, start: int, end: int) -> None:
    self.parent = parent
    self.location = location
    self.start = start
    self.end = end
    self.pf = PassFail()
    self.positive_pf = PassFail()
    self.output_pf = PassFail()
    self.update_count: int = 0
    self.total_case_info: int = 0
    self.case_update_count: int = 0
    self.out_dist: float = -1.0
    self.out_dist_map: Dict[int, float] = dict()
    self.same_seapr_pf = PassFail(1, 1)
    self.diff_seapr_pf = PassFail(1, 1)
    self.patch_rank: int = -1
  def __hash__(self) -> int:
    return hash(self.location)
  def __eq__(self, other) -> bool:
    return self.location == other.location

class RecoderTypeInfo:
  def __init__(self, parent: LineInfo, act: str, prev: 'RecoderTypeInfo') -> None:
    self.parent = parent
    self.act = act
    self.prev = prev
    self.next: Dict[str, 'RecoderTypeInfo'] = dict()
    self.pf = PassFail()
    self.positive_pf = PassFail()
    self.output_pf = PassFail()
    self.update_count: int = 0
    self.total_case_info: int = 0
    self.case_update_count: int = 0
    self.out_dist: float = -1.0
    self.score_list: List[float] = list()
    self.out_dist_map: Dict[int, float] = dict()
    self.recoder_case_info_map: Dict[int, RecoderCaseInfo] = dict()
  def is_root(self) -> bool:
    return self.prev is None
  def is_leaf(self) -> bool:
    return len(self.next) == 0
  def get_root(self) -> 'RecoderTypeInfo':
    if self.prev is None:
      return self
    return self.prev.get_root()
  def get_path(self) -> List['RecoderTypeInfo']:
    if not self.is_leaf():
      return list()
    type_info = self
    path = [type_info]
    while not type_info.is_root():
      type_info = type_info.prev
      path.append(type_info)
    return path
  def __hash__(self) -> int:
    return hash(self.act)
  def __eq__(self, other) -> bool:
    return self.act == other.act

class RecoderCaseInfo:
  def __init__(self, parent: LineInfo, location: str, case_id: int) -> None:
    self.parent = parent
    self.location = location
    self.case_id = case_id
    self.pf = PassFail()
    self.positive_pf = PassFail()
    self.output_pf = PassFail()
    self.update_count: int = 0
    self.total_case_info: int = 0
    self.case_update_count: int = 0
    self.out_dist: float = -1.0
    self.prob: float = 0
    self.out_dist_map: Dict[int, float] = dict()
    self.same_seapr_pf = PassFail(1, 1)
    self.diff_seapr_pf = PassFail(1, 1)
    self.patch_rank: int = -1
  def __hash__(self) -> int:
    return hash(self.location)
  def __eq__(self, other) -> bool:
    return self.location == other.location
  def to_str(self) -> str:
    return f"{self.parent.line_id}-{self.case_id}"

# Find with f"{file_name}:{line_number}"
class FileLine:
  def __init__(self, fi: FileInfo, li: LineInfo, score: float) -> None:
    self.file_info = fi
    self.line_info = li
    self.score = score
    self.case_map: Dict[str, TbarCaseInfo] = dict() # switch_number-case_number -> TbarCaseInfo
    self.seapr_e_pf: PassFail = PassFail()
    self.seapr_n_pf: PassFail = PassFail()
    # self.type_map: Dict[PatchType, Tuple[PassFail, PassFail]] = dict()
  def to_str(self) -> str:
    return f"{self.file_info.file_name}:{self.line_info.line_number}"
  def __str__(self) -> str:
    return self.to_str()
  def __hash__(self) -> int:
    return hash(self.to_str())
  def __eq__(self, other) -> bool:
    return self.file_info == other.file_info and self.line_info == other.line_info

class LocationScore:
  def __init__(self,file:str,line:int,primary_score:int,secondary_score:int):
    self.file_name=file
    self.line=line
    self.primary_score=primary_score
    self.secondary_score=secondary_score
  def __eq__(self,object):
    if object is None or type(object)!=LocationScore:
      return False
    else:
      if self.file_name==object.file_name and self.line==object.line:
        return True
      else:
        return False

class MSVEnvVar:
  def __init__(self) -> None:
    pass
  @staticmethod
  def get_new_env_tbar(state: 'MSVState', patch: 'TbarPatchInfo', test: str) -> Dict[str, str]:
    new_env = os.environ.copy()
    new_env["MSV_UUID"] = str(state.uuid)
    new_env["MSV_TEST"] = str(test)
    new_env["MSV_LOCATION"] = str(patch.tbar_case_info.location)
    new_env["MSV_WORKDIR"] = state.work_dir if not state.fixminer_mode else state.work_dir[:-2]
    new_env["MSV_BUGGY_LOCATION"] = patch.file_info.file_name
    new_env["MSV_BUGGY_PROJECT"] = state.d4j_buggy_project
    new_env["MSV_OUTPUT_DISTANCE_FILE"] = f"/tmp/{uuid.uuid4()}.out"
    new_env["MSV_TIMEOUT"] = str(state.timeout)
    if patch.file_info.class_name != "":
      new_env["MSV_CLASS_NAME"] = patch.file_info.class_name
    return new_env
  @staticmethod
  def get_new_env_recoder(state: 'MSVState', patch: 'RecoderPatchInfo', test: str) -> Dict[str, str]:
    new_env = os.environ.copy()
    new_env["MSV_UUID"] = str(state.uuid)
    new_env["MSV_TEST"] = str(test)
    new_env["MSV_LOCATION"] = str(patch.recoder_case_info.location)
    new_env["MSV_WORKDIR"] = state.work_dir
    new_env["MSV_BUGGY_LOCATION"] = patch.file_info.file_name
    new_env["MSV_BUGGY_PROJECT"] = state.d4j_buggy_project
    new_env["MSV_OUTPUT_DISTANCE_FILE"] = f"/tmp/{uuid.uuid4()}.out"
    new_env["MSV_TIMEOUT"] = str(state.timeout)
    new_env["MSV_RECODER"] = "-"
    return new_env
  @staticmethod
  def get_new_env_d4j_positive_tests(state: 'MSVState', tests: List[str], new_env: Dict[str, str]) -> Dict[str, str]:
    # test_list = f"/tmp/{uuid.uuid4()}.list"
    # new_env["MSV_TEST_LIST"] = test_list
    # with open(test_list, "w") as f:
    #   for test in tests:
    #     f.write(test + "\n")
    new_env["MSV_TEST"] = "ALL"
    return new_env

class TbarPatchInfo:
  def __init__(self, tbar_case_info: TbarCaseInfo) -> None:
    self.tbar_case_info = tbar_case_info
    self.tbar_type_info = tbar_case_info.parent
    self.line_info = self.tbar_type_info.parent
    self.func_info = self.line_info.parent
    self.file_info = self.func_info.parent
    self.out_dist = -1.0
    self.out_diff = False
  def update_result(self, result: bool, n: float, b_n:float,exp_alpha: bool, fixed_beta: bool) -> None:
    self.tbar_case_info.pf.update(result, n,b_n, exp_alpha, fixed_beta)
    self.tbar_type_info.pf.update(result, n,b_n, exp_alpha, fixed_beta)
    self.line_info.pf.update(result, n,b_n, exp_alpha, fixed_beta)
    self.func_info.pf.update(result, n,b_n,exp_alpha, fixed_beta)
    self.file_info.pf.update(result, n,b_n, exp_alpha, fixed_beta)
  def update_result_out_dist(self, state: 'MSVState', result: bool, dist: float, test: int) -> None:
    self.out_dist = dist
    is_diff = True
    if test in state.original_output_distance_map:
      is_diff = dist != state.original_output_distance_map[test]
    tmp = self.tbar_case_info.update_count * self.tbar_case_info.out_dist
    self.tbar_case_info.out_dist = (tmp + dist) / (self.tbar_case_info.update_count + 1)
    self.tbar_case_info.update_count += 1
    self.tbar_case_info.output_pf.update(is_diff, 1.0)
    tmp = self.tbar_type_info.update_count * self.tbar_type_info.out_dist
    self.tbar_type_info.out_dist = (tmp + dist) / (self.tbar_type_info.update_count + 1)
    self.tbar_type_info.update_count += 1
    self.tbar_type_info.output_pf.update(is_diff, 1.0)
    tmp = self.line_info.update_count * self.line_info.out_dist
    self.line_info.out_dist = (tmp + dist) / (self.line_info.update_count + 1)
    self.line_info.update_count += 1
    self.line_info.output_pf.update(is_diff, 1.0)
    tmp = self.func_info.update_count * self.func_info.out_dist
    self.func_info.out_dist = (tmp + dist) / (self.func_info.update_count + 1)
    self.func_info.update_count += 1
    self.func_info.output_pf.update(is_diff, 1.0)
    tmp = self.file_info.update_count * self.file_info.out_dist
    self.file_info.out_dist = (tmp + dist) / (self.file_info.update_count + 1)
    self.file_info.update_count += 1
    self.file_info.output_pf.update(is_diff, 1.0)    
  def update_result_positive(self, result: bool, n: float, b_n:float,exp_alpha: bool, fixed_beta: bool) -> None:
    self.tbar_case_info.positive_pf.update(result, n,b_n, exp_alpha, fixed_beta)
    self.tbar_type_info.positive_pf.update(result, n,b_n, exp_alpha, fixed_beta)
    self.line_info.positive_pf.update(result, n,b_n, exp_alpha, fixed_beta)
    self.func_info.positive_pf.update(result, n,b_n, exp_alpha, fixed_beta)
    self.file_info.positive_pf.update(result, n,b_n, exp_alpha, fixed_beta)
  def remove_patch(self, state: 'MSVState') -> None:
    if self.tbar_case_info.location not in self.tbar_type_info.tbar_case_info_map:
      state.msv_logger.critical(f"{self.tbar_case_info.location} not in {self.tbar_type_info.tbar_case_info_map}")
    del self.tbar_type_info.tbar_case_info_map[self.tbar_case_info.location]
    if len(self.tbar_type_info.tbar_case_info_map) == 0:
      del self.line_info.tbar_type_info_map[self.tbar_type_info.mutation]
    if len(self.line_info.tbar_type_info_map) == 0:
      score = self.line_info.fl_score
      self.func_info.fl_score_list.remove(score)
      self.file_info.fl_score_list.remove(score)
      del self.func_info.line_info_map[self.line_info.uuid]
      state.score_remain_line_map[self.line_info.fl_score].remove(self.line_info)
      if len(state.score_remain_line_map[self.line_info.fl_score])==0:
        state.score_remain_line_map.pop(self.line_info.fl_score)
      self.func_info.remain_lines_by_score[self.line_info.fl_score].remove(self.line_info)
      if len(self.func_info.remain_lines_by_score[self.line_info.fl_score])==0:
        self.func_info.remain_lines_by_score.pop(self.line_info.fl_score)
      self.file_info.remain_lines_by_score[self.line_info.fl_score].remove(self.line_info)
      if len(self.file_info.remain_lines_by_score[self.line_info.fl_score])==0:
        self.file_info.remain_lines_by_score.pop(self.line_info.fl_score)
    if len(self.func_info.line_info_map) == 0:
      del self.file_info.func_info_map[self.func_info.id]
      state.func_list.remove(self.func_info)
    if len(self.file_info.func_info_map) == 0:
      del state.file_info_map[self.file_info.file_name]
    self.tbar_case_info.case_update_count += 1
    self.tbar_type_info.case_update_count += 1
    self.tbar_type_info.remain_patches_by_score[self.line_info.fl_score].remove(self.tbar_case_info)
    self.line_info.case_update_count += 1
    self.line_info.remain_patches_by_score[self.line_info.fl_score].remove(self.tbar_case_info)
    self.func_info.case_update_count += 1
    self.func_info.remain_patches_by_score[self.line_info.fl_score].remove(self.tbar_case_info)
    self.file_info.case_update_count += 1
    self.file_info.remain_patches_by_score[self.line_info.fl_score].remove(self.tbar_case_info)
    state.java_remain_patch_ranking[self.line_info.fl_score].remove(self.tbar_case_info)
    if len(state.java_remain_patch_ranking[self.line_info.fl_score])==0:
      state.java_remain_patch_ranking.pop(self.line_info.fl_score)
    self.func_info.searched_patches_by_score[self.line_info.fl_score]+=1

  def to_json_object(self) -> dict:
    conf = dict()
    conf["location"] = self.tbar_case_info.location
    return conf
  def to_str(self) -> str:
    return f"{self.tbar_case_info.location}"
  def __str__(self) -> str:
    return self.to_str()
  def to_str_sw_cs(self) -> str:
    return self.to_str()
  @staticmethod
  def list_to_str(selected_patch: list) -> str:
    result = list()
    for patch in selected_patch:
      result.append(patch.to_str())
    return ",".join(result)
  
class RecoderPatchInfo:
  def __init__(self, recoder_case_info: RecoderCaseInfo) -> None:
    self.recoder_case_info = recoder_case_info
    # self.recoder_type_info = recoder_case_info.parent # leaf node
    # self.recoder_type_info_list = self.recoder_type_info.get_path()
    self.line_info = self.recoder_case_info.parent
    self.func_info = self.line_info.parent
    self.file_info = self.func_info.parent
    self.out_dist = -1.0
    self.out_diff = False
  def update_result(self, result: bool, n: float, b_n:float,exp_alpha: bool, fixed_beta: bool) -> None:
    self.recoder_case_info.pf.update(result, n,b_n, exp_alpha, fixed_beta)
    # for rti in self.recoder_type_info_list:
    #   rti.pf.update(result, n,b_n, exp_alpha, fixed_beta)
    # self.recoder_type_info.pf.update(result, n,b_n, exp_alpha, fixed_beta)
    self.line_info.pf.update(result, n,b_n, exp_alpha, fixed_beta)
    self.func_info.pf.update(result, n,b_n, exp_alpha, fixed_beta)
    self.file_info.pf.update(result, n,b_n, exp_alpha, fixed_beta)
  def update_result_out_dist(self, state: 'MSVState', result: bool, dist: float, test: int) -> None:
    self.out_dist = dist
    is_diff = True
    if test in state.original_output_distance_map:
      is_diff = dist != state.original_output_distance_map[test]
    tmp = self.recoder_case_info.update_count * self.recoder_case_info.out_dist
    self.recoder_case_info.out_dist = (tmp + dist) / (self.recoder_case_info.update_count + 1)
    self.recoder_case_info.update_count += 1
    self.recoder_case_info.output_pf.update(is_diff, 1.0)
    # tmp = self.recoder_type_info.update_count * self.recoder_type_info.out_dist
    # self.recoder_type_info.out_dist = (tmp + dist) / (self.recoder_type_info.update_count + 1)
    # self.recoder_type_info.update_count += 1
    # self.recoder_type_info.output_pf.update(is_diff, 1.0)
    tmp = self.line_info.update_count * self.line_info.out_dist
    self.line_info.out_dist = (tmp + dist) / (self.line_info.update_count + 1)
    self.line_info.update_count += 1
    self.line_info.output_pf.update(is_diff, 1.0)
    tmp = self.func_info.update_count * self.func_info.out_dist
    self.func_info.out_dist = (tmp + dist) / (self.func_info.update_count + 1)
    self.func_info.update_count += 1
    self.func_info.output_pf.update(is_diff, 1.0)
    tmp = self.file_info.update_count * self.file_info.out_dist
    self.file_info.out_dist = (tmp + dist) / (self.file_info.update_count + 1)
    self.file_info.update_count += 1
    self.file_info.output_pf.update(is_diff, 1.0)    
  def update_result_positive(self, result: bool, n: float, b_n:float,exp_alpha: bool, fixed_beta: bool) -> None:
    self.recoder_case_info.positive_pf.update(result, n,b_n, exp_alpha, fixed_beta)
    # self.recoder_type_info.positive_pf.update(result, n,b_n, exp_alpha, fixed_beta)
    # for rti in self.recoder_type_info_list:
    #   rti.positive_pf.update(result, n,b_n, exp_alpha, fixed_beta)
    self.line_info.positive_pf.update(result, n,b_n, exp_alpha, fixed_beta)
    self.func_info.positive_pf.update(result, n,b_n, exp_alpha, fixed_beta)
    self.file_info.positive_pf.update(result, n,b_n, exp_alpha, fixed_beta)
  def remove_patch(self, state: 'MSVState') -> None:
    if self.recoder_case_info.case_id not in self.line_info.recoder_case_info_map:
      state.msv_logger.critical(f"{self.recoder_case_info.case_id} not in {self.line_info.recoder_case_info_map}")
    del self.line_info.recoder_case_info_map[self.recoder_case_info.case_id]
    # if len(self.recoder_type_info.recoder_case_info_map) == 0:
    #   del self.line_info.recoder_type_info_map[self.recoder_type_info.mode]
    # for rti in self.recoder_type_info_list:
    #   if len(rti.next) == 0 and len(rti.recoder_case_info_map) == 0:
    #     if rti.prev is not None:
    #       del rti.prev.next[rti.act]
    #     else:
    #       del self.line_info.recoder_type_info_map[rti.act]
    if len(self.line_info.recoder_case_info_map) == 0:
      score = self.line_info.fl_score
      self.func_info.fl_score_list.remove(score)
      self.file_info.fl_score_list.remove(score)
      del self.func_info.line_info_map[self.line_info.uuid]
      state.score_remain_line_map[self.line_info.fl_score].remove(self.line_info)
      if len(state.score_remain_line_map[self.line_info.fl_score])==0:
        state.score_remain_line_map.pop(self.line_info.fl_score)
      self.func_info.remain_lines_by_score[self.line_info.fl_score].remove(self.line_info)
      if len(self.func_info.remain_lines_by_score[self.line_info.fl_score])==0:
        self.func_info.remain_lines_by_score.pop(self.line_info.fl_score)
      self.file_info.remain_lines_by_score[self.line_info.fl_score].remove(self.line_info)
      if len(self.file_info.remain_lines_by_score[self.line_info.fl_score])==0:
        self.file_info.remain_lines_by_score.pop(self.line_info.fl_score)
    if len(self.func_info.line_info_map) == 0:
      del self.file_info.func_info_map[self.func_info.id]
      state.func_list.remove(self.func_info)
    if len(self.file_info.func_info_map) == 0:
      del state.file_info_map[self.file_info.file_name]
    prob = self.recoder_case_info.prob
    # self.recoder_type_info.score_list.remove(prob)
    self.line_info.score_list.remove(prob)
    self.func_info.score_list.remove(prob)
    self.file_info.score_list.remove(prob)
    self.recoder_case_info.case_update_count += 1
    # self.recoder_type_info.case_update_count += 1
    # for rti in self.recoder_type_info_list:
    #   rti.case_update_count += 1
    #   rti.score_list.remove(prob)
    self.line_info.case_update_count += 1
    fl_score = self.line_info.fl_score
    self.line_info.remain_patches_by_score[fl_score].remove(self.recoder_case_info)
    self.func_info.case_update_count += 1
    self.func_info.remain_patches_by_score[fl_score].remove(self.recoder_case_info)
    self.file_info.case_update_count += 1
    self.file_info.remain_patches_by_score[fl_score].remove(self.recoder_case_info)
    state.java_remain_patch_ranking[fl_score].remove(self.recoder_case_info)
    if len(state.java_remain_patch_ranking[self.line_info.fl_score])==0:
      state.java_remain_patch_ranking.pop(self.line_info.fl_score)
    self.func_info.searched_patches_by_score[fl_score] += 1
  def to_json_object(self) -> dict:
    conf = dict()
    conf["location"] = self.recoder_case_info.location
    conf["id"] = self.line_info.line_id
    conf["case_id"] = self.recoder_case_info.case_id
    return conf
  def to_str(self) -> str:
    return f"{self.recoder_case_info.location}"
  def __str__(self) -> str:
    return self.to_str()
  def to_str_sw_cs(self) -> str:
    return f"{self.line_info.line_id}-{self.recoder_case_info.case_id}"
  @staticmethod
  def list_to_str(selected_patch: list) -> str:
    result = list()
    for patch in selected_patch:
      result.append(patch.to_str())
    return ",".join(result)

@dataclass
class MSVResult:
  iteration: int
  time: float
  config: List[TbarPatchInfo]
  result: bool
  pass_result: bool
  pass_all_neg_test: bool
  output_distance: float
  def __init__(self, execution: int, iteration:int,time: float, config: List[TbarPatchInfo], result: bool,pass_test_result:bool=False, output_distance: float = 100.0, pass_all_neg_test: bool = False, compilable: bool = True) -> None:
    self.execution = execution
    self.iteration=iteration
    self.time = time
    self.config = config
    self.result = result
    self.pass_result=pass_test_result
    self.pass_all_neg_test = pass_all_neg_test
    self.compilable = compilable
    self.output_distance = output_distance
    self.out_diff = config[0].out_diff
  def to_json_object(self,total_searched_patch:int=0,total_passed_patch:int=0,total_plausible_patch:int=0) -> dict:
    object = dict()
    object["execution"] = self.execution
    object['iteration']=self.iteration
    object["time"] = self.time
    object["result"] = self.result
    object['pass_result']=self.pass_result
    object["output_distance"] = self.output_distance
    object["out_diff"] = self.out_diff
    object["pass_all_neg_test"] = self.pass_all_neg_test
    object["compilable"] = self.compilable

    # This total counts include this result
    object['total_searched']=total_searched_patch
    object['total_passed']=total_passed_patch
    object['total_plausible']=total_plausible_patch
    conf_list = list()
    for patch in self.config:
      conf = patch.to_json_object()
      conf_list.append(conf)
    object["config"] = conf_list
    return object

@dataclass()
class MSVState:
  msv_logger: logging.Logger
  original_args: List[str]
  args: List[str]
  msv_version: str
  mode: MSVMode
  msv_path: str
  work_dir: str
  out_dir: str
  msv_uuid: str
  use_simulation_mode: bool
  prev_data: str
  cycle: int
  timeout: int
  start_time: float
  last_save_time: float
  is_alive: bool
  use_condition_synthesis: bool
  use_fl: bool
  use_prophet_score: bool
  use_hierarchical_selection: int
  use_pass_test: bool
  use_multi_line: int
  use_partial_validation: bool
  ignore_compile_error: bool
  time_limit: int
  cycle_limit: int
  correct_case_info: TbarCaseInfo
  correct_patch_str: str
  watch_level: str
  max_parallel_cpu: int
  new_revlog: str
  patch_info_map: Dict[str, FileInfo]  # fine_name: str -> FileInfo
  file_info_map: Dict[str, FileInfo]   # file_name: str -> FileInfo
  switch_case_map: Dict[str, Union[TbarCaseInfo, TbarCaseInfo, RecoderCaseInfo]] # f"{switch_number}-{case_number}" -> SwitchCase
  patch_location_map: Dict[str, Union[TbarCaseInfo, RecoderCaseInfo]]
  selected_patch: List[TbarPatchInfo] # Unused
  selected_test: List[int]        # Unused
  used_patch: List[MSVResult]
  negative_test: List[int]        # Negative test case
  positive_test: List[int]        # Positive test case
  d4j_negative_test: List[str]
  d4j_positive_test: List[str]
  d4j_failed_passing_tests: Set[str]
  d4j_test_fail_num_map: Dict[str, int]
  priority_list: List[Tuple[str, int, float]]  # (file_name, line_number, score)
  priority_map: Dict[str, FileLine] # f"{file_name}:{line_number}" -> FileLine
  msv_result: List[dict]   # List of json object by MSVResult.to_json_object()
  failed_positive_test: Set[int] # Set of positive test that failed
  tmp_dir: str
  max_dist: float
  function_to_location_map: Dict[str, Tuple[str, int, int]] # function_name -> (file_name, line_start, line_end)
  test_to_location: Dict[int, Dict[str, Set[int]]] # test_number -> {file_name: set(line_number)}
  use_pattern: bool      # For SeAPR mode
  simulation_data: Dict[str, dict] # patch_id -> fail_result, pass_result, fail_time, pass_time. compile_result
  max_initial_trial: int
  c_map: Dict[PT, float]
  params: Dict[PT, float]
  params_decay: Dict[PT, float]
  original_output_distance_map: Dict[int, float]
  tbar_mode: bool
  recoder_mode: bool
  use_exp_alpha: bool
  patch_ranking: List[str]
  ranking_map: Dict[str, int]
  total_basic_patch: int
  bounded_seapr: bool
  def __init__(self) -> None:
    self.msv_version = "1.0.0"
    self.mode = MSVMode.guided
    self.msv_path = ""
    self.msv_uuid = str(uuid.uuid4())
    self.cycle = 0
    self.total_basic_patch = 0
    self.start_time = time.time()
    self.last_save_time = self.start_time
    self.is_alive = True
    self.use_condition_synthesis = False
    self.use_fl = False
    self.use_prophet_score = False
    self.use_hierarchical_selection = 1
    self.use_pass_test = False
    self.use_multi_line = 1
    self.skip_valid=False
    self.use_fixed_beta=False
    self.time_limit = -1
    self.cycle_limit = -1
    self.max_parallel_cpu = 8
    self.new_revlog = ""
    self.patch_info_map = dict()
    self.switch_case_map = dict()
    self.selected_patch = None
    self.file_info_map = dict()
    self.negative_test = list()
    self.positive_test = list()
    self.d4j_negative_test = list()
    self.d4j_positive_test = list()
    self.d4j_failed_passing_tests = set()
    self.d4j_test_fail_num_map = dict()
    self.d4j_buggy_project: str = ""
    self.patch_location_map = dict()
    self.profile_map = dict()
    self.priority_list = list()
    self.fl_score:List[LocationScore]=list()
    self.line_list:List[LineInfo]=list()
    self.msv_result = list()
    self.var_counts=dict()
    self.failed_positive_test = set()
    self.use_cpr_space=False
    self.priority_map = dict()
    self.use_fixed_const=False
    self.used_patch = list()
    self.critical_map = dict()
    self.profile_diff = None
    self.timeout = 60000
    self.uuid=uuid.uuid1()
    self.tmp_dir = "/tmp"
    self.max_dist = 100.0
    self.function_to_location_map = dict()
    self.test_to_location = dict()
    self.use_pattern = False
    self.use_simulation_mode = False
    self.prev_data = ""
    self.ignore_compile_error = True
    self.simulation_data = dict()
    self.correct_patch_str: str = ""
    self.correct_case_info: TbarCaseInfo = None
    self.watch_level: str = ""
    self.total_searched_patch=0
    self.total_passed_patch=0
    self.total_plausible_patch=0
    self.iteration=0
    self.orig_rank_iter=0
    self.use_partial_validation = True
    self.max_initial_trial = 0
    self.c_map = {PT.basic: 1.0, PT.plau: 1.0, PT.fl: 1.0, PT.out: 0.0}
    self.params = {PT.basic: 1.0, PT.plau: 1.0, PT.fl: 1.0, PT.out: 0.0, PT.cov: 2.0, PT.sigma: 0.0, PT.halflife: 1.0, PT.epsilon: 0.0,PT.b_dec:0.0,PT.a_init:2.0,PT.b_init:2.0}
    self.params_decay = {PT.fl:1.0,PT.basic:1.0,PT.plau:1.0}
    self.original_output_distance_map = dict()
    self.use_msv_ext=False
    self.tbar_mode = False
    self.recoder_mode = False
    self.prapr_mode=False
    self.use_exp_alpha = False
    self.run_all_test=False
    self.regression_php_mode=''
    self.top_fl=0
    self.patch_ranking = list()
    self.use_fixed_halflife=False
    self.regression_test_info:List[int]=list()
    self.language_model_path='./Google-word2vec.txt'
    self.language_model_mean=''
    self.remove_cached_file=False
    self.use_epsilon=True
    self.finish_at_correct_patch=False
    self.func_list: List[FuncInfo] = list()
    self.count_compile_fail=True
    self.fixminer_mode=False  # fixminer-mode: Fixminer patch space is seperated to 2 groups
    self.spr_mode=False  # SPR mode: SPR uses FL+template instead of prophet score
    self.sampling_mode=False  # sampling mode: use Thompson-sampling to select patch
    self.finish_top_method=False  # Finish if every patches in top-30 methods are searched. Should turn on for default SeAPR
    self.use_unified_debugging=False  # Use unified debugging to generate more precise clusters

    self.seapr_remain_cases:List[TbarCaseInfo]=[]
    self.seapr_layer:SeAPRMode=SeAPRMode.FUNCTION
    self.bounded_seapr = False
    self.ranking_map = dict()

    self.c_patch_ranking:Dict[float,List[TbarCaseInfo]]=dict()
    self.c_remain_patch_ranking:Dict[float,List[TbarCaseInfo]]=dict()
    self.java_patch_ranking:Dict[float,List[TbarCaseInfo]]=dict()
    self.java_remain_patch_ranking:Dict[float,List[TbarCaseInfo]]=dict()
    self.score_remain_line_map:Dict[float,List[LineInfo]]=dict()  # Remaining lines by each scores(FL, prophet score, ...)

    self.previous_score:float=0.0
    self.same_consecutive_score:Dict[float,int]=dict()
    self.MAX_CONSECUTIVE_SAME_SCORE=50
    self.max_prophet_score=-1000.
    self.min_prophet_score=1000.
    self.max_epsilon_group_size=0  # Maximum size of group for epsilon-greedy

    self.not_use_guided_search=False  # Use only epsilon-greedy search
    self.not_use_epsilon_search=False  # Use only guided search and original
    self.not_use_acceptance_prob=True  # Always use vertical search
    self.test_time=0.  # Total compile and test time
    self.select_time=0.  # Total select time
    self.total_methods=0  # Total methods

    self.correct_patch_list:List[str]=[]  # List of correct patch ids

    # Under here is for fixminer sub-template patches.
    # We will swap both primary- and sub-template data when every primary-patches are tried.
    self.sub_file_info_map = dict()
    self.sub_total_methods = 0
    self.sub_line_list = list()
    self.sub_func_list = list()
    self.sub_priority_map = dict()
    self.sub_patch_ranking = list()
    self.sub_java_patch_ranking = dict()
    self.sub_java_remain_patch_ranking = dict()
    self.sub_max_epsilon_group_size = 0
    self.fixminer_swapped=False

  def fixminer_swap_info(self):
    if not self.fixminer_swapped:
      self.sub_file_info_map,self.file_info_map=self.file_info_map,self.sub_file_info_map
      self.sub_total_methods,self.total_methods=self.total_methods,self.sub_total_methods
      self.sub_line_list,self.line_list=self.line_list,self.sub_line_list
      self.sub_func_list,self.func_list=self.func_list,self.sub_func_list
      self.sub_priority_map,self.priority_map=self.priority_map,self.sub_priority_map
      self.sub_patch_ranking,self.patch_ranking=self.patch_ranking,self.sub_patch_ranking
      self.sub_java_patch_ranking,self.java_patch_ranking=self.java_patch_ranking,self.sub_java_patch_ranking
      self.sub_java_remain_patch_ranking,self.java_remain_patch_ranking=self.java_remain_patch_ranking,self.sub_java_remain_patch_ranking
      self.sub_max_epsilon_group_size,self.max_epsilon_group_size=self.max_epsilon_group_size,self.sub_max_epsilon_group_size
      self.fixminer_swapped=True

def remove_file_or_pass(file:str):
  try:
    if os.path.exists(file):
      os.remove(file)
  except:
    pass

def record_to_int(record: List[bool]) -> List[int]:
  """
    Convert boolean written record to binary list.

    record: record written in bool
    return: record written in 0 or 1
  """
  result=[]
  for path in record:
    result.append(1 if path else 0)
  return result

def append_java_cache_result(state:MSVState,case:TbarCaseInfo,fail_result:bool,pass_result:bool,pass_all_fail:bool,compilable:bool,
      fail_time:float, pass_time:float):
  """
    Append result to cache file, if not exist. Otherwise, do nothing.
    
    state: MSVState
    case: current patch
    fail_result: result of fail test (bool)
    pass_result: result of pass test (bool)
    fail_time: fail time (second)
    pass_time: pass time (second)
  """
  id=case.location
  if id not in state.simulation_data:
    current=dict()
    current['basic']=fail_result
    current['plausible']=pass_result
    current['pass_all_fail']=pass_all_fail
    current['compilable']=compilable
    current['fail_time']=fail_time
    current['pass_time']=pass_time

    state.simulation_data[id]=current
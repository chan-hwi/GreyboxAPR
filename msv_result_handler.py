from matplotlib.patches import Patch
from core import *
from typing import List, Set, Dict, Tuple

def update_result(state: MSVState, selected_patch: List[PatchInfo], run_result: bool, n: float, test: int) -> None:
  critical_pf = PassFail()
  if state.use_hierarchical_selection >= 2:
    original_profile = state.profile_map[test]
    profile = Profile(state, f"{test}-{selected_patch[0].to_str_sw_cs()}")
    critical_pf = original_profile.get_critical_diff(profile, run_result)
    state.msv_logger.debug(
        f"Critical PF: {critical_pf.pass_count}/{critical_pf.fail_count}")
  for patch in selected_patch:
    patch.update_result(run_result, n,state.use_fixed_beta)
    patch.update_result_critical(critical_pf,state.use_fixed_beta)

def update_result_critical(state: MSVState, selected_patch: List[PatchInfo], run_result: bool, test: int) -> None:
  pass

def update_result_positive(state: MSVState, selected_patch: List[PatchInfo], run_result: bool, failed_tests: Set[int]) -> None:
  run_result = (len(failed_tests) == 0)
  for patch in selected_patch:
    patch.update_result_positive(run_result, len(failed_tests))

def save_result(state: MSVState) -> None:
  state.last_save_time = time.time()
  result_file = os.path.join(state.out_dir, "msv-result.json")
  state.msv_logger.info(f"Saving result to {result_file}")
  with open(result_file, 'w') as f:
    json.dump(state.msv_result, f, indent=2)


# Append result list, save result to file periodically
def append_result(state: MSVState, selected_patch: List[PatchInfo], test_result: bool,pass_test_result:bool=False) -> None:
  save_interval = 10
  tm = time.time()
  tm_interval = tm - state.start_time
  result = MSVResult(state.cycle, tm_interval,
                     selected_patch, test_result,pass_test_result)
  state.msv_result.append(result.to_json_object())
  if (tm - state.last_save_time) > save_interval:
    save_result(state)

def remove_patch(state: MSVState, patches: List[PatchInfo]) -> None:
  for patch in patches:
    patch.remove_patch(state)

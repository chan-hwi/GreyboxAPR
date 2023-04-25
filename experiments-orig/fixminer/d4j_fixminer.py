
CHART_SIZE=26
CLOSURE_SIZE=133
LANG_SIZE=65
MATH_SIZE=106
MOCKITO_SIZE=38
TIME_SIZE=27

CHART_CORRECT=(1,4,11,19,19002) # 24: sub
CLOSURE_CORRECT=(10,38,62,63,73)
LANG_CORRECT=(57,59)
MATH_CORRECT=(22,22002,30,34,35,35002,57,70,75,79,82) # 85: infinite test for buggy, 33: too large iter
MOCKITO_CORRECT=(29,38)
# TIME_CORRECT=(19,) # 19: too large iter

LANG_SKIP=(2,)
MOCKITO_SKIP=(9,10,11,21)

CHART_PLAUSIBLE=(12,13,14,15,17,25,3,7)
CLOSURE_PLAUSIBLE=(129,19)
LANG_PLAUSIBLE=(63,)
MATH_PLAUSIBLE=(20,33,50,63,84) # 50, 63: need check, 80, 81: infinite test
TIME_PLAUSIBLE=(11,19) # 11: need check

CLI_SIZE=40
CODEC_SIZE=18
COLLECTIONS_SIZE=28
COMPRESS_SIZE=47
CSV_SIZE=16
GSON_SIZE=18
JACKSON_CORE_SIZE=26
JACKSON_DATABIND_SIZE=112
JACKSON_XML_SIZE=6
JSOUP_SIZE=93
JXPATH_SIZE=22
CLOSURE_NEW=[i for i in range(133,175)]

CLI_SKIP=(6,)
COLLECTIONS_SKIP=(1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,19,20,21,22,23,24)
JACKSON_DATABIND_SKIP=[]
for i in range(58,113):
    JACKSON_DATABIND_SKIP.append(i)
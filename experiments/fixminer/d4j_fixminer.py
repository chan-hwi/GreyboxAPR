
CHART_SIZE=26
CLOSURE_SIZE=133
LANG_SIZE=65
MATH_SIZE=106
MOCKITO_SIZE=38
TIME_SIZE=27

MOCKITO_SKIP=(9,10,11,21)

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
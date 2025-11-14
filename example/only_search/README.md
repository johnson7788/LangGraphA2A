#  并行搜索回答
1. 根据问题，使用plan agent创建N个搜索计划。
2. execute agent并行执行每个搜索
3. 搜索资料存储在state中，得到有用的检索结果。
4. 方便Summary Agent使用这些有用的检索结果。

# 注意tool需要修改，改成自己的搜索
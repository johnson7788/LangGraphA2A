#  Plan-Execute-Summary Agent， 主要用于任务规划，然后进行任务执行并解决问题。
1. 根据问题，使用plan agent 列出计划。
2. execute agent按顺序执行计划中的每一步。
3. 执行如果出问题，fix plan Agent会进行执行计划修改。
4. 所有步骤执行完毕，summary agent生成总结。

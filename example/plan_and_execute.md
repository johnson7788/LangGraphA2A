# 计划和执行
flowchart LR
  START([START]) --> planner[planner]
  planner --> agent[agent]
  agent --> replan[replan]
  replan -->|has response| END([END])
  replan -->|need more steps| agent


# 日志记录
2025-08-29 13:08:32 | INFO | plan_and_execute | === App starting ===
2025-08-29 13:08:32 | INFO | plan_and_execute | Run | query='2025年苹果有哪些新品发布?'
2025-08-29 13:08:35 | INFO | plan_and_execute | Planner | start planning for input: '2025年苹果有哪些新品发布?'
2025-08-29 13:08:43 | INFO | plan_and_execute | Planner | generated 5 step(s)
2025-08-29 13:09:00 | INFO | plan_and_execute | StreamEvent | node=planner | dict(keys=[plan...])
2025-08-29 13:09:41 | INFO | plan_and_execute | ExecuteStep | executing step 1: 检查苹果公司官方网站或新闻发布会的公告，以获取2025年新品发布的信息。
2025-08-29 13:10:11 | INFO | plan_and_execute | WebSearch | query='site:apple.com 2025 new product announcement'
2025-08-29 13:10:40 | INFO | plan_and_execute | WebSearch | parsed 15 results
2025-08-29 13:12:32 | INFO | plan_and_execute | StreamEvent | node=agent | dict(keys=[past_steps...])
2025-08-29 13:12:34 | INFO | plan_and_execute | Replanner | deciding next action (done_steps=1)
2025-08-29 13:13:15 | INFO | plan_and_execute | Replanner | produced updated plan with 4 step(s)
2025-08-29 13:13:44 | INFO | plan_and_execute | StreamEvent | node=replan | dict(keys=[plan...])
2025-08-29 13:13:48 | INFO | plan_and_execute | ExecuteStep | executing step 1: 访问科技新闻网站，如The Verge、TechCrunch或CNET，查找关于苹果2025年新品发布的报道。
2025-08-29 13:14:56 | INFO | plan_and_execute | WebSearch | query='site:theverge.com Apple 2025 new product launch'
2025-08-29 13:14:57 | INFO | plan_and_execute | WebSearch | parsed 15 results
2025-08-29 13:14:57 | INFO | plan_and_execute | WebSearch | query='site:techcrunch.com Apple 2025 new product launch'
2025-08-29 13:14:59 | INFO | plan_and_execute | WebSearch | parsed 10 results
2025-08-29 13:14:59 | INFO | plan_and_execute | WebSearch | query='site:cnet.com Apple 2025 new product launch'
2025-08-29 13:14:59 | INFO | plan_and_execute | WebSearch | parsed 15 results
2025-08-29 13:15:12 | INFO | plan_and_execute | StreamEvent | node=agent | dict(keys=[past_steps...])
2025-08-29 13:15:12 | INFO | plan_and_execute | Replanner | deciding next action (done_steps=2)
2025-08-29 13:15:23 | INFO | plan_and_execute | Replanner | produced final response
2025-08-29 13:15:23 | INFO | plan_and_execute | Graph | should_end -> END (final response present)
2025-08-29 13:15:27 | INFO | plan_and_execute | StreamEvent | node=replan | dict(keys=[response...])
2025-08-29 13:15:27 | INFO | plan_and_execute | === App finished ===
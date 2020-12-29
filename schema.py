SCHEMA = [
    'featured',  # 是否为精选评价，如果是则无法获取评价日期
    'covid-19',  # 是否涉及COVID19内容
    'anonymous',  # 是否是匿名评价，如果是则无法获取地点和职位
    'date',  # 评价的日期，如果是精选评价则无评价日期
    'time',  # 评价的时间，如果是精选评价则无评价时间
    'headline',  # 评价的标题
    'role',  # 评级人的职位，如果是匿名评价则无法获取
    'location',  # 评价人的地点，如果是匿名评价则无法获取
    'status',  # 评价人的雇佣状态，是否离职，可能缺失
    'contract',  # 评价人的合同类型，全职还是兼职，抑或其他的
    'years',  # 工作年限
    'helpful',  # 评价的赞数
    'pros',  # 公司的优点，被隐藏
    'cons',  # 公司的缺点，被隐藏
    'advice_to_mgmt',  # 对管理层建议，被隐藏
    'main_rating',  # 总体的评分
    'work_life_balance',  # work/life balance，需要匹配
    'culture_and_values',  # culture & values，需要匹配
    'diversity_inclusion',  # diversity & inclusion，需要匹配
    'career_opportunities',  # career opportunities，需要匹配
    'comp_and_benefits',  # compensation & benefits，需要匹配
    'senior_management',  # senior management，需要匹配
    'recommends',  # 推荐度，可能缺失
    'outlook',  # 未来6月展望如何，可能缺失
    'CEO_approval'  # 对ceo认同度，可能缺失
]

def create_schedule_llm(goal: str) -> str:
    SYSTEM_PROMP = (
        "You are an assistant with scheduling abilities and the ability "
        "to perform recurring tasks based on user goals. Please create a"
        "schedule from the following goal."
    )

    AUTO_SCHEDULE_PROMPT = f"""
    You are a reliable assistant, please help the user schedule with their goal, and the output is a single JSON in json block format.
    If time is not given, set it as 00:00:00 keep datetime format is "YYYY-MM-DD HH:MM:SS".
    if dont have schedule_start_at or schedule_end_at set them as empty string.

    Example 1:
    [GOAL]
    Send daily news and start from November 11, 2025, at 9 AM daily, send everyday in 5 years.
    [OUTPUT]
    ```json
        {{
            "name": "Daily News Delivery",
            "description": "Send daily news updates",
            "is_recurring": true,
            "schedule_start_at": "2025-11-11 09:00:00",
            "schedule_end_at": "2030-11-11 09:00:00",
            "schedule_interval": "0 9 * * *"
        }}
    ```
    Example 2:
    [GOAL]
    Send an email inviting them to a meeting every Thursday at 8 a.m.
    [OUTPUT]
    ```json
        {{
            "name": " Send an email inviting them to a meeting",
            "description": " Send an email inviting them to a meeting every Thursday at 8 a.m",
            "is_recurring": true,
            "schedule_start_at": "",
            "schedule_end_at": "",
            "schedule_interval": "0 8 * * 4"
        }}
    ```
    Example 3:
    [GOAL]
    Send invitation letter for parents' meeting on 18/2/2025  at 16h pm.
    [OUTPUT]
    ```json
        {{
            "name": "Invitation Letter for Parents' Meeting",
            "description": "Send invitation letter for parents' meeting on 18/2/2025 at 16h pm",
            "is_recurring": false,
            "schedule_start_at": "2025-02-18 16:00:00",
            "schedule_end_at": "",
            "schedule_interval": ""
        }}
    ```
    ######
    [GOAL]
    {goal}

    [OUTPUT]

"""
    return SYSTEM_PROMP, AUTO_SCHEDULE_PROMPT

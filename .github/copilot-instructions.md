this agent is designed for auto gencode and load agent skill at runtime.
that can write python skill code and save to file system, then load and execute the skill code at runtime via chat interaction. or schedule job 


một dự án automus agent cho phép tự viết code cho chính nó tự tạo skill 

nó hỗ trợ 2 dạng skill

- skills dạng python code 
    nó sẽ viết skill rồi nếu biên dịch thành công thì nó sẽ thêm vào thư viện của nó 
- skills dạng llm (bản chất là một file markdown để hướng dẫn)


Agent này nó sẽ có các job chạy liên tục: nó sẽ suy nghĩ liên tục để làm những việc mà nó được giao hoặc cải tiến chính nó.


sonagent/agents

chứa các agent của hệ thống 
trong đó có main agent là agent điều phối tất cả các agent còn lại,
nó chủ yếu hỏi đáp giao tiếp với người dùng, tạo task, kiểm tra trạng thái của các task, kill một task mà một agent nào đó đang chạy 

agent_registry
đăng ký các agent hiện có và có kênh giao tiếp giữa các agent, main agent có thể lấy dữ liệu giao tiếp và trạng thái được các sub agent update ở đây cũng như các agent hiện có, để trả lời người dùng

sonagent/agent.py
Phụ trách việc load  main agent và subagent, agent registry
sonagent/skills/skills_manager.py
sẽ định kỳ scan skills folder, và load skill cho các agent tương ứng 




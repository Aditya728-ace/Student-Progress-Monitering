# 📊🎓 EduInsight - Monitoring Progress, Guiding Growth.

### 📝 Overview
This project is a comprehensive web application designed to facilitate quiz management for teachers and provide in-depth student performance analysis. Built with Flask, SQLAlchemy, and integrated with Firebase Firestore, it aims to empower educators with data-driven insights to identify student strengths and weaknesses, enabling personalized guidance and targeted educational interventions. 🚀

### ✨ Features

#### 🧑‍🏫 Teacher Interface
*   **User Authentication:** Secure login/signup with role-based access (Teacher). 🔐
*   **Quiz Creation & Management:**
    *   Add new quizzes with multiple questions and choices. ➕
    *   Edit existing quizzes (update name, questions, choices, correct answers). ✏️
    *   Delete quizzes. 🗑️
    *   All quiz modifications are synchronized with Firebase Firestore for real-time updates and cloud persistence. ☁️
*   **Student Performance Monitoring:**
    *   View all student quiz results in a centralized dashboard. 📈
    *   **Advanced Filtering:** Filter results by individual student or specific quiz. 🔍
    *   **Subject-wise Analysis:** Identify overall class performance on particular subjects. 📚
    *   **Individual Student Progress:** Analyze a student's performance across all quizzes to pinpoint strong and weak subjects. 💪🎯
    *   **Data Export:** Download comprehensive CSV reports for:
        *   Individual student's complete quiz history (e.g., `Student1_complete_results.csv`). 📥
        *   All students' results for a specific quiz/subject (e.g., `Geography (All student).csv`). 🌍
    *   **Student Account Management:** Delete student accounts and their associated local results. ❌

#### 🧑‍🎓 Student Interface
*   **User Authentication:** Secure login/signup with role-based access (Student). 🔑
*   **Quiz Taking:** Access and attempt available quizzes. ✍️
*   **Instant Results:** View quiz scores immediately upon submission. ✅
*   **Personal Result History:** Access a dashboard displaying their past quiz results. 📊

#### 💾 Data Management & Persistence
*   **SQLAlchemy (SQLite):** Used for core application data (users, quizzes, questions) and individual student quiz results (stored in separate SQLite databases per student for isolation). 🗄️
*   **Firebase Firestore:** Integrated for cloud synchronization of user accounts, quiz definitions, and student quiz results, ensuring data integrity, real-time updates, and scalability. ☁️🔄
*   **Analytical Focus:** Designed to provide data for identifying learning patterns and guiding personalized education. 🧠💡

### 💻 Technical Stack
*   **Backend:** Python, Flask 🐍
*   **Database (Local):** SQLite (managed via SQLAlchemy ORM) 🗄️
*   **Database (Cloud):** Google Cloud Firestore (Firebase) 🔥
*   **Frontend:** HTML, CSS (Jinja2 templating) 🎨
*   **Authentication:** Session-based management 🛡️
*   **Data Export:** CSV generation 📄

### 🧑‍💻 Made By
* This project was developed by Aditya Jayant Ahirrao

# 🅿️ ParkSense

**ParkSense** is an intelligent parking management system designed to simplify how users find, reserve, and manage parking spaces.  
Built with Python and SQLite, it offers real-time tracking, clean data handling, and easy setup — all in a lightweight package.

---

## 🚗 Overview

ParkSense helps you:
- Track **available parking spots** in real time  
- Manage **vehicle entries and exits** with accuracy  
- Generate **usage and revenue reports**  
- Run seamlessly with a simple **SQLite database**  
- Deploy quickly using **Flask** for the web interface

---

## 🧠 Features

- 🔍 **Real-Time Availability** — Know instantly which spaces are free or occupied  
- 📋 **Vehicle Management** — Add, update, or remove records easily  
- 📈 **Usage Analytics** — Generate insights on parking trends  
- 💾 **Lightweight Database** — Uses SQLite, no external setup needed  
- 🌐 **Web-Based Access** — Flask-powered dashboard for easy interaction  

---

## ⚙️ Tech Stack

| Layer | Technology |
|-------|-------------|
| Backend | **Python 3.x** |
| Framework | **Flask** |
| Database | **SQLite 3** |
| Environment | **Replit / Localhost** |

---

## 🚀 Getting Started

### ✅ Prerequisites
Make sure you have:
- Python 3.x  
- SQLite (comes pre-installed with Python)  
- Flask (`pip install flask`)  
- Git (optional)

---

### 🧩 Installation

Clone and set up the project:

```bash
git clone https://github.com/JoanathanPS/ParkSense.git
cd ParkSense
pip install -r requirements.txt
```

Start the server:

```bash
python app.py
```

Access it at:

```
http://localhost:5000
```

---

## 🗃️ Database Structure

### `Book` Table
| Column | Type | Description |
|--------|------|-------------|
| accession_no | INTEGER | Unique ID for each book |
| title | TEXT | Book title |
| publisher | TEXT | Publisher name |
| author | TEXT | Author name |
| status | TEXT | `issued` / `available` / `sent_for_binding` |
| date_of_purchase | DATE | Purchase date |

### `Vehicle` Table
| Column | Type | Description |
|--------|------|-------------|
| id | INTEGER | Vehicle ID |
| plate_number | TEXT | License plate number |
| owner_name | TEXT | Vehicle owner |
| slot_number | TEXT | Assigned parking slot |
| check_in_time | DATETIME | Entry time |
| check_out_time | DATETIME | Exit time |

---

## 🧠 Example Usage

- Add a new parking entry  
- Update slot availability  
- View reports of all active and historical vehicles  
- Delete or archive old entries  

---

## 🧰 Future Enhancements

- 🚙 QR-based entry system  
- 📱 Mobile app integration  
- 🔔 Real-time notifications for slot availability  
- 🌍 Multi-lot management

---

## 🧑‍💻 Author

**Joanathan P. S.**  
Project maintained with 💡 curiosity and clean Python code.  
📫 Reach out via GitHub: [JoanathanPS](https://github.com/JoanathanPS)

---

## 📸 Preview

<img src="https://github.com/user-attachments/assets/b5aa9c0d-33bb-4bed-b118-5494160e45ed" alt="ParkSense Screenshot" width="800"/>

---

## 🪪 License

This project is licensed under the **MIT License** — see the [LICENSE](LICENSE) file for details.

---

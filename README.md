# Smart Resource Booking & Allocation Platform

A web-based resource booking and allocation platform developed using Flask and integrated with Git, GitHub, Jenkins, Docker, and Ansible to demonstrate an automated DevOps CI/CD workflow.

---

## Project Overview

The Smart Resource Booking & Allocation Platform helps institutions manage shared resources such as laboratories, classrooms, meeting rooms, halls, and equipment.

The application provides separate workflows for administrators and users.

### Administrator Features

- Add institutional resources
- Edit resource details
- Change resource availability
- View all booking requests
- Approve booking requests
- Reject booking requests
- Cancel bookings
- Monitor resource and booking statistics

### User Features

- Browse available resources
- Search and filter resources
- Submit booking requests
- View booking history
- Track booking status
- Cancel their own bookings

---

## Technology Stack

### Application

- Python
- Flask
- Flask-Login
- SQLAlchemy
- HTML5
- CSS3
- JavaScript

### Testing

- Pytest

### DevOps

- Git
- GitHub
- Jenkins
- Docker
- Ansible
- WSL

---

## Application Architecture

```text
                    Smart Resource Booking
                             |
             +---------------+---------------+
             |                               |
          Admin                            User
             |                               |
     Resource Management             Browse Resources
     Booking Management              Submit Requests
     Approve / Reject                Track Bookings
             |                               |
             +---------------+---------------+
                             |
                        Flask Backend
                             |
                         Database


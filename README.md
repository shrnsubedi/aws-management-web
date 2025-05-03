# ☁️ AWS EC2 Management Dashboard (Flask App)
Erasmus Mundus Master in Green Networking and Cloud Computing (Module: Cloud Services)

This is a Flask-based web application designed to interface with AWS services, specifically EC2. It provides a lightweight dashboard for interacting with your AWS environment via the AWS SDK (Boto3), offering operations like listing regions and potential EC2 instance management.

## Features

- Flask-based web frontend  
- AWS EC2 integration using Boto3  
- Region listing functionality  
- Clean, minimal HTML interface (via Jinja2 templates)

## Project Structure

```
.
├── app.py               # Main Flask app
├── templates/
│   └── index.html       # HTML template for the homepage
```

## Technologies Used

- Python 3  
- Flask  
- Boto3 (AWS SDK for Python)  
- HTML (Jinja2 templating)

## Setup Instructions

1. Clone the repository:

```
git clone https://github.com/yourusername/aws-ec2-dashboard.git
cd aws-ec2-dashboard
```

2. Install dependencies:

It's recommended to use a virtual environment.

```
pip install flask boto3
```

3. Configure AWS credentials:

Set your AWS credentials using one of the following methods:

- Edit your `~/.aws/credentials` and `~/.aws/config` files  
- Or use environment variables:

```
export AWS_ACCESS_KEY_ID=your_access_key  
export AWS_SECRET_ACCESS_KEY=your_secret_key  
export AWS_DEFAULT_REGION=your_region  
```

4. Run the app:

```
python app.py
```

Then open your browser and go to:

```
http://127.0.0.1:5000
```


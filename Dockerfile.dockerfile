FROM python:3.11.9

RUN apt update && \
    apt upgrade -y

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV TZ=Asia/Amman
ENV DEBUG = True

# Set the working directory in the container
WORKDIR /app

# Install system dependencies
RUN apt-get update \
    && apt-get install -y gcc tzdata \
    && apt-get clean

# Install Python dependencies
COPY requirements.txt /app/
RUN pip install --upgrade pip
RUN pip install --no-cache-dir -r requirements.txt

# Copy the entire Django project into the working directory in the container
COPY . /app/
RUN python manage.py collectstatic

# Run migrations and create superuser
# RUN python manage.py drop_all_tables
# RUN #python manage.py flush
RUN python manage.py makemigrations
RUN python manage.py migrate
# RUN python manage.py createsuperuser --no-input || true
RUN python manage.py collectstatic --noinput

EXPOSE 8000

# Start the Django app
#CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]
CMD ["python", "-m", "uvicorn", "dgFramework.asgi:application", "--host", "0.0.0.0", "--port", "8000"]

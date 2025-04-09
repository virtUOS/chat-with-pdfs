FROM python:3.13-slim
EXPOSE 8501

# Install dependencies
COPY requirements.txt /chat-with-pdfs/requirements.txt
RUN pip install --no-cache-dir -r /chat-with-pdfs/requirements.txt

# Copy the current directory contents into the container at /app
COPY . /chat-with-pdfs
WORKDIR /chat-with-pdfs

# Set the user to 'nobody' for security
USER nobody

# Healthcheck to ensure the app is running
HEALTHCHECK CMD curl --fail http://localhost:8501/_stcore/health || exit 1

# Run the Streamlit app
ENTRYPOINT ["streamlit", "run", "app.py", "--server.port=8501", "--server.address=0.0.0.0"]
FROM mcr.microsoft.com/playwright/python:v1.56.0-noble

# Install AWS Lambda Runtime Interface Client and other dependencies
RUN apt-get update && \
    apt-get install -y \
    g++ \
    make \
    cmake \
    unzip \
    libcurl4-openssl-dev \
    && rm -rf /var/lib/apt/lists/*

# Install AWS Lambda Runtime Interface Client
RUN pip install awslambdaric

# Set working directory to Lambda task root
WORKDIR /var/task

# Copy requirements and install Python dependencies
COPY requirements.txt /var/task/
RUN pip install --no-cache-dir -r requirements.txt

# Install Playwright browsers (they should already be in the base image)
RUN python -m playwright install --with-deps chromium

# Set environment variables for Nova Act and Playwright
ENV PLAYWRIGHT_BROWSERS_PATH=/ms-playwright
ENV PLAYWRIGHT_SKIP_BROWSER_DOWNLOAD=1
ENV NOVA_ACT_SKIP_PLAYWRIGHT_INSTALL=1
ENV NOVA_ACT_BROWSER_ARGS="--disable-gpu --disable-dev-shm-usage --no-sandbox --single-process"

# Copy function code
COPY lambda_function.py /var/task/

# Set the entrypoint and command for Lambda
ENTRYPOINT [ "/usr/bin/python", "-m", "awslambdaric" ]
CMD [ "lambda_function.lambda_handler" ]
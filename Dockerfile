FROM ://microsoft.com

# Install system dependencies for Lean (if any specific ones are needed)
RUN apt-get update && apt-get install -y dotnet-sdk-6.0

# Create a virtual environment and set it as the default
ENV VIRTUAL_ENV=/opt/venv
RUN python3 -m venv $VIRTUAL_ENV
ENV PATH="$VIRTUAL_ENV/bin:$PATH"

# Install Lean and other requirements
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt


FROM ubuntu:latest
RUN apt-get update && apt-get -y update
# 3.6 is the latest Python on stock Ubuntu 20.X right now. Grr!
RUN apt-get install -y build-essential python3.6 python3-pip python3-dev git
RUN pip3 -q install pip --upgrade

# RUN mkdir src
# WORKDIR src/
# Copy entire onya.dj source dir
# WORKDIR creates the dir if it doesn't exist
WORKDIR /notebook
COPY . .

RUN pip3 install git+https://github.com/uogbuji/onya@main
RUN pip3 install -r ./notebook/requirements.notebook.txt
RUN pip3 install .
RUN pip3 install jupyter
RUN pip3 freeze | grep notebook
RUN pip3 freeze | grep onya

WORKDIR /

# Docker run is expected to be run with a volume mount at /sdb for the Serato DB

#ENV port 8888
#CMD ["jupyter", "notebook", "--port=${port}", "--no-browser", "--ip=0.0.0.0", "--allow-root"]
CMD ["jupyter", "notebook", "--port=8888", "--no-browser", "--ip=0.0.0.0", "--allow-root", "--NotebookApp.token=''", "--NotebookApp.password=''"]


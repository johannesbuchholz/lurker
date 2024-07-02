FROM python:3.9.19-bookworm as base

WORKDIR /lurker

# setup python dependencies
ENV PYTHONDONTWRITEBYTECODE=1
COPY requirements.txt ./
RUN pip install -r requirements.txt

# add lurker user
RUN addgroup lurker
RUN adduser --system --no-create-home --ingroup lurker --disabled-password lurker

# copy source files
RUN mkdir "src"
COPY --chown=lurker:lurker --chmod=r src/ src/
COPY --chown=lurker:lurker --chmod=rx __main__.py ./

# add speech recognition model
RUN mkdir "models"
COPY --chown=lurker:lurker --chmod=r misc/models/tiny.pt ./models/

# without this, sounddevice can not load library PortAudio
RUN apt-get update && apt-get install -y libportaudio2

USER lurker
ENTRYPOINT ["python", "__main__.py"]
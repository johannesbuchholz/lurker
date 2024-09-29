# whisper module seems to be only installable on a "full" debian distribution.
FROM python:3.9.19-slim-bookworm

WORKDIR /lurker

# setup python dependencies
ENV PYTHONDONTWRITEBYTECODE=1
COPY requirements.txt ./
RUN pip install -r requirements.txt

# without this, sounddevice can not load library PortAudio or query sound devices
RUN apt update && apt install -y libportaudio2 alsa-utils

# add lurker user
RUN adduser --system --ingroup audio lurker

# copy source files
RUN mkdir "src"
COPY --chown=lurker:lurker --chmod=r src/ src/
COPY --chown=lurker:lurker --chmod=rx __main__.py ./

# add speech recognition model
RUN mkdir "models"
COPY --chown=lurker:lurker --chmod=r lurker/models/tiny.pt models
ENV LURKER_MODEL=/lurker/models/tiny.pt

# add empty dir to mount configuration into
RUN mkdir "home"

USER lurker
ENTRYPOINT ["python", "__main__.py"]
CMD ["--lurker-home", "/lurker/home"]
# Lurker

Ein besserer Name kommt bestimmt noch.

## Quellen zum weiteren Vertiefen
- Mozilla DeepSpeech: https://deepspeech.readthedocs.io/en/r0.9/index.html
  - GitHub: https://github.com/mozilla/DeepSpeech
  - Pre-Trained Models: https://deepspeech.readthedocs.io/en/r0.9/USING.html#getting-the-pre-trained-model
  - 

## Test setup für statisches audio
Lasse in diesem verzeichnis laufen
```
deepspeech --model deepspeech-0.9.3-models.pbmm --scorer deepspeech-0.9.3-models.scorer --audio test-audio.wav
```

## Requirements
- Lade deepspeech models:
  - https://deepspeech.readthedocs.io/en/r0.9/USING.html#getting-the-pre-trained-model
    - Größe "Model" etwa 180MB, Größe "Scorer" etwa 900MB
      - ```commandline
        wget https://github.com/mozilla/DeepSpeech/releases/download/v0.9.3/deepspeech-0.9.3-models.pbmm
        wget https://github.com/mozilla/DeepSpeech/releases/download/v0.9.3/deepspeech-0.9.3-models.scorer
        ```
- Installiere in virtual environment mittels `pip3 install --require-virtualenv -r requirements.txt`
import os

os.environ.setdefault("OMP_NUM_THREADS", "1")
os.environ.setdefault("MKL_NUM_THREADS", "1")
os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")
os.environ.setdefault("NUMEXPR_NUM_THREADS", "1")

from TTS.tts.configs.shared_configs import BaseDatasetConfig
from TTS.tts.configs.tacotron2_config import Tacotron2Config
from TTS.tts.models.tacotron2 import Tacotron2
from TTS.config.shared_configs import BaseAudioConfig

output_path = "./my_waifu_model"

# Set up dataset config
dataset_config = BaseDatasetConfig(
    formatter="ljspeech",
    meta_file_train="metadata.csv",
    path="my_waifu_dataset"
)

# Model config
config = Tacotron2Config(
    audio=BaseAudioConfig(sample_rate=22050),
    run_name="waifu_tacotron2",
    num_chars=148,
    batch_size=4,
    eval_batch_size=2,
    num_loader_workers=0,
    num_eval_loader_workers=0,
    run_eval=False,
    test_delay_epochs=-1,
    epochs=500,
    text_cleaner="english_cleaners",
    output_path=output_path,
    datasets=[dataset_config]
)

# Start training
model = Tacotron2(config)
model.fit()

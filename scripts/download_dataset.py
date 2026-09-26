import os
from dotenv import load_dotenv
from roboflow import Roboflow

load_dotenv()

rf = Roboflow(api_key=os.environ["ROBOFLOW_API_KEY"])
project = rf.workspace("roboflow-universe-projects").project("construction-site-safety")
version = project.version(27)
dataset = version.download("yolov8", location="data/ppe_dataset")

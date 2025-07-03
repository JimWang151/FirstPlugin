# Made by Jim.Wang V1 for ComfyUI
import sys


python = sys.executable

from .FirstPlugin import FeishuTableReader,XMLBatchSceneReader,NewsAPI_Fetcher,Parse_News_Content

NODE_CLASS_MAPPINGS = {
    "FeishuTableReader":FeishuTableReader,
    "XMLSceneReader":XMLBatchSceneReader,
    "NewsAPI_Fetcher":NewsAPI_Fetcher,
    "Parse_News_Content":Parse_News_Content
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "FeishuTableReader":"Read Scene Information",
    "XMLBatchSceneReader":"Get Scene Prompt",
    "NewsAPI_Fetcher":"Get MyShell News",
    "Parse_News_Content":"Parse News Content"
}






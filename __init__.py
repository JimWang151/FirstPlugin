# Made by Jim.Wang V1 for ComfyUI
import sys


python = sys.executable

from .FirstPlugin import FeishuTableReader,XMLBatchSceneReader,NewsAPI_Fetcher,Parse_News_Content,Parse_XML_News,String_Slicer

NODE_CLASS_MAPPINGS = {
    "FeishuTableReader":FeishuTableReader,
    "XMLSceneReader":XMLBatchSceneReader,
    "NewsAPI_Fetcher":NewsAPI_Fetcher,
    "Parse_News_Content":Parse_News_Content,
    "Parse_XML_News":Parse_XML_News,
    "String_Slicer":String_Slicer
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "FeishuTableReader":"Read Scene Information",
    "XMLBatchSceneReader":"Get Scene Prompt",
    "NewsAPI_Fetcher":"Get MyShell News",
    "Parse_News_Content":"Parse News Content",
    "Parse_XML_News":"Parse XML News",
    "String_Slicer":"String Slicer"
}






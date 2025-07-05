import pdfplumber
import io
import os
from typing import Optional
from app.core.config import settings


def extract_text_from_pdf(file_path: str) -> Optional[str]:
    """Extract text from PDF file using Google Cloud Vision OCR"""
    
    # Ensure Google credentials are set
    if settings.google_application_credentials:
        os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = settings.google_application_credentials
    
    try:
        text = ""
        
        with pdfplumber.open(file_path) as pdf:
            for page_num, page in enumerate(pdf.pages):
                # First try direct text extraction
                page_text = page.extract_text()
                
                if page_text and page_text.strip():
                    text += page_text + "\n"
                else:
                    # Use Google Cloud Vision OCR
                    try:
                        from google.cloud import vision
                        
                        # Convert page to image
                        page_image = page.to_image(resolution=200)
                        
                        # Convert PIL image to bytes
                        img_byte_arr = io.BytesIO()
                        page_image.original.save(img_byte_arr, format='PNG')
                        img_byte_arr.seek(0)
                        
                        # Initialize Vision client
                        client = vision.ImageAnnotatorClient()
                        
                        # Create image object
                        image = vision.Image(content=img_byte_arr.getvalue())
                        
                        # Perform OCR
                        response = client.text_detection(image=image)
                        
                        if response.text_annotations:
                            ocr_text = response.text_annotations[0].description
                            if ocr_text:
                                text += ocr_text + "\n"
                                print(f"Google Vision extracted {len(ocr_text)} characters from page {page_num + 1}")
                        
                    except Exception as ocr_error:
                        print(f"Google Vision OCR failed for page {page_num + 1}: {ocr_error}")
                        continue
        
        return text.strip() if text.strip() else None
        
    except Exception as e:
        print(f"Error extracting text from {file_path}: {e}")
        return None


def extract_text_from_uploaded_file(file_content: bytes) -> Optional[str]:
    """Extract text from uploaded PDF file content using Google Vision"""
    
    # Ensure Google credentials are set
    if settings.google_application_credentials:
        os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = settings.google_application_credentials
    
    try:
        text = ""
        
        with pdfplumber.open(io.BytesIO(file_content)) as pdf:
            for page_num, page in enumerate(pdf.pages):
                page_text = page.extract_text()
                
                if page_text and page_text.strip():
                    text += page_text + "\n"
                else:
                    try:
                        from google.cloud import vision
                        
                        page_image = page.to_image(resolution=200)
                        
                        img_byte_arr = io.BytesIO()
                        page_image.original.save(img_byte_arr, format='PNG')
                        img_byte_arr.seek(0)
                        
                        client = vision.ImageAnnotatorClient()
                        image = vision.Image(content=img_byte_arr.getvalue())
                        response = client.text_detection(image=image)
                        
                        if response.text_annotations:
                            ocr_text = response.text_annotations[0].description
                            if ocr_text:
                                text += ocr_text + "\n"
                        
                    except Exception as ocr_error:
                        continue
        
        return text.strip() if text.strip() else None
        
    except Exception as e:
        return None

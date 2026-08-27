from PyPDF2 import PdfReader
import re
from datetime import datetime, timedelta


def process_authors(authors):
    """ Process the authors string from PDF metadata and return a list of authors."""
    if authors:
        # first remove any " and " or & 
        authors = re.sub(r'\s+and\s+|&', ',', authors)
        # Split authors by common delimiters and strip whitespace
        author_list = [author.strip() for author in re.split(r'[;,]', authors) if author.strip()]
        return author_list
    return []


def process_date(date_str):
    """ Process the date string from PDF metadata and return it in a standard format (YYYY-MM-DD HH:MM:SS)."""
    if date_str:
        # Remove the 'D:' prefix if present
        if date_str.startswith('D:'):
            date_str = date_str[2:]

        try:
            match = re.search(r'([+-])(\d{1,2})\'(\d{2})\'', date_str)

            if match:
                sign = 1 if match.group(1) == '+' else -1
                hours_offset = int(match.group(2))
                minutes_offset = int(match.group(3))

                # Parse the base date part (e.g., 20121031133848)
                base_date_str = re.sub(r'[+-]\d{1,2}\'\d{2}\Z', '', date_str)
                parsed_base_date = datetime.strptime(base_date_str, '%Y%m%d%H%M%S')

                # Calculate the total offset in minutes
                offset_minutes = sign * (hours_offset * 60 + minutes_offset)

                # Adjust the base date by the offset to get UTC time
                adjusted_datetime = parsed_base_date - timedelta(minutes=offset_minutes)
                # Format the adjusted datetime as YYYY-MM-DD HH:MM:SS
                formatted_date = adjusted_datetime.strftime('%Y-%m-%d %H:%M:%S')
                return formatted_date
            else:
                # If no timezone offset, assume it's already in UTC format (e.g., 20120929154703Z)
                parsed_date = datetime.strptime(date_str, '%Y%m%d%H%M%SZ')
                formatted_date = parsed_date.strftime('%Y-%m-%d %H:%M:%S')
                return formatted_date
        except ValueError:
            print(f"Date parsing error for {date_str}")
    return None


def extract_metadata(pdf_path):
    """ Extract metadata from a PDF file."""
    metadata = {}
    
    try:
        with open(pdf_path, 'rb') as f:
            reader = PdfReader(f)
            doc_info = reader.metadata
            metadata['Title'] = doc_info.title if doc_info.title else None
            metadata['Author'] = doc_info.author if doc_info.author else None
            metadata['Subject'] = doc_info.subject if doc_info.subject else None
            metadata['Creator'] = doc_info.creator if doc_info.creator else None
            metadata['Producer'] = doc_info.producer if doc_info.producer else None
            metadata['CreationDate'] = doc_info['/CreationDate'] if '/CreationDate' in doc_info else None
            metadata['ModDate'] = doc_info['/ModDate'] if '/ModDate' in doc_info else None
            metadata['Keywords'] = doc_info['/Keywords'] if '/Keywords' in doc_info else None
            metadata['Trapped'] = doc_info['/Trapped'] if '/Trapped' in doc_info else None
            metadata['NumberOfPages'] = len(reader.pages)
    except Exception as e:
        print(f"Error extracting metadata from {pdf_path}: {e}")

    metadata['Author'] = process_authors(metadata.get('Author'))
    metadata['CreationDate'] = process_date(metadata.get('CreationDate'))
    metadata['ModDate'] = process_date(metadata.get('ModDate'))
    
    return metadata
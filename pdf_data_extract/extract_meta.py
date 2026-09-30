import logging
import re
from datetime import datetime, timedelta

import pymupdf

logger = logging.getLogger(__name__)


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
            logger.warning("Date parsing error for %s", date_str)
    return None


def extract_metadata(pdf_path):
    """ Extract metadata from a PDF file."""
    metadata = {}

    try:
        with pymupdf.open(pdf_path) as document:
            info = document.metadata or {}
            metadata['Title'] = info.get('title') or None
            metadata['Author'] = info.get('author') or None
            metadata['Subject'] = info.get('subject') or None
            metadata['Creator'] = info.get('creator') or None
            metadata['Producer'] = info.get('producer') or None
            metadata['CreationDate'] = info.get('creationDate') or None
            metadata['ModDate'] = info.get('modDate') or None
            metadata['Keywords'] = info.get('keywords') or None
            trapped = info.get('trapped')
            metadata['Trapped'] = trapped if trapped not in (None, '') else None
            metadata['NumberOfPages'] = document.page_count
    except Exception as e:
        logger.warning("Error extracting metadata from %s: %s", pdf_path, e)

    metadata['Author'] = process_authors(metadata.get('Author'))
    metadata['CreationDate'] = process_date(metadata.get('CreationDate'))
    metadata['ModDate'] = process_date(metadata.get('ModDate'))
    
    return metadata
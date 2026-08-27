import pdf_data_processing

def main():
    folder_path = '/home/py1sl/papers/'  # Replace with your folder path
    metadata = pdf_data_processing.process_papers_folder(folder_path)
    
    if metadata:
        print("Extracted Metadata:")
        for data in metadata:
            for key, value in data.items():
                print(f"{key}: {value}")
            print("-" * 20)
    else:
        print("No metadata found.")

if __name__ == "__main__":
    main()
from www.services import *


def get_data(input, database, df, reset_callback=None):
    """
    Handle the data upload and display process.
    
    Args:
        input: An object that provides user input methods.
        database: The name of the database.
        df: A DataFrame object to store the data.
        reset_callback: Function to call to reset analysis results (optional)
        
    Returns:
        A message indicating the status of the data upload.
    """
    # 1D — API retrieval (no file required)
    if input.select() == "1D":
        try:
            query = input.api_query() if hasattr(input, "api_query") else ""
            source = input.api_source() if hasattr(input, "api_source") else "openalex"
            max_results = int(input.api_max_results()) if hasattr(input, "api_max_results") else 100
            if not query.strip():
                text = ui.div(ui.h5("Please enter a search query.", style="color: orange;"))
            else:
                from www.services.etl.pipeline import run_api_pipeline
                result_df, _, _ = run_api_pipeline(query, platform=source, max_records=max_results)
                df.set(result_df)
                if reset_callback:
                    reset_callback()
                source_label = "PubMed API" if source == "pubmed_api" else "OpenAlex"
                text = ui.p(
                    f"{source_label} query '{query}' completed. "
                    f"Retrieved {len(result_df)} records "
                    f"({result_df.shape[1]} columns)."
                )
        except Exception as e:
            text = ui.div(
                ui.h5("Error fetching data from API:", style="color: red;"),
                ui.p(str(e), style="color: red;"),
            )
        return text

    file: list[FileInfo] | None = input.Dataset()

    if file is None:
        text = ui.h5("Please select a file to begin importing your data.")

    elif input.select() == "1A":
        ui.update_action_button("action_button_save", disabled=False)
        
        source = input.database()
        author = input.author()
        
        try:
            # Check if multiple files are selected
            if len(file) > 1:
                # Process multiple files
                json = process_multiple_files(file, source, author)
                df.set(pd.read_json(StringIO(json)))
                # Reset all analysis results when new dataset is loaded
                if reset_callback:
                    reset_callback()
                text = ui.p(
                    f"{database}'s files uploaded and processed successfully! "
                    f"{len(file)} files have been processed and combined. "
                    f"The dataset contains {df.get().shape[0]} rows and {df.get().shape[1]} columns."
                )
            else:
                # Process single file (original logic)
                type = file[0]["name"]
                json = biblio_json(file[0]["datapath"], source, type, author)
                df.set(pd.read_json(StringIO(json)))
                # Reset all analysis results when new dataset is loaded
                if reset_callback:
                    reset_callback()
                
                if type.endswith(".zip"):
                    text = ui.p(
                        f"{database}'s ZIP archive uploaded and extracted successfully! "
                        f"Multiple files have been processed and combined. "
                        f"The dataset contains {df.get().shape[0]} rows and {df.get().shape[1]} columns."
                    )
                else:
                    text = ui.p(
                        f"{database}'s file uploaded successfully! You can now proceed to analyze your data. "
                        f"The dataset contains {df.get().shape[0]} rows and {df.get().shape[1]} columns."
                    )
        except Exception as e:
            text = ui.div(
                ui.h5("Error processing file(s):", style="color: red;"),
                ui.p(str(e), style="color: red;"),
                ui.p("Please check that your files are in the correct format and try again.", style="color: gray;")
            )

    elif input.select() == "1B":
        df.set(pd.read_excel(file[0]["datapath"]))
        # Reset all analysis results when new dataset is loaded
        if reset_callback:
            reset_callback()
        text = ui.p(
            f"{database}'s file uploaded successfully! You can now proceed to analyze your data. "
            f"The dataset contains {df.get().shape[0]} rows and {df.get().shape[1]} columns."
        )

    else:
        text = ""

    return text

import streamlit as st
import tempfile
from document_processor import DocumentProcessor, ExtractedDocument, Contract, ComparisonResult
from typing import List, Tuple, Optional, Dict
import json
import os
from dotenv import load_dotenv
from logging_config import logger

# Load environment variables
load_dotenv()

# Initialize session state for contracts and invoices
if 'contracts' not in st.session_state:
    st.session_state.contracts = []
    logger.info("Initialized contracts list in session state")
if 'invoices' not in st.session_state:
    st.session_state.invoices = []
    logger.info("Initialized invoices list in session state")
if 'extracted_data' not in st.session_state:
    st.session_state.extracted_data = {}
    logger.info("Initialized extracted_data dict in session state")

def verify_state():
    """Verify the state of stored data."""
    logger.info("Verifying session state...")
    logger.info(f"Number of contracts: {len(st.session_state.contracts)}")
    logger.info(f"Number of invoices: {len(st.session_state.invoices)}")
    logger.info(f"Number of extracted data entries: {len(st.session_state.extracted_data)}")
    
    # Log contract details
    for i, contract in enumerate(st.session_state.contracts):
        logger.info(f"Contract {i+1}: ID={contract.id}, Supplier={contract.supplier_name}")
    
    # Log invoice details
    for i, invoice in enumerate(st.session_state.invoices):
        logger.info(f"Invoice {i+1}: Name={invoice['name']}")

def display_document_info(doc: ExtractedDocument):
    """Display document information in a formatted way."""
    logger.info("Displaying document information")
    st.json({
        "Invoice Number": doc.invoice_number,
        "Supplier Name": doc.supplier_name,
        "Issue Date": doc.issue_date,
        "Due Date": doc.due_date,
        "Subtotal": doc.subtotal,
        "Tax": doc.tax,
        "Total": doc.total
    })
    
    # Display line items in a table
    if doc.items:
        logger.debug(f"Displaying {len(doc.items)} line items")
        st.subheader("Line Items")
        items_data = []
        for item in doc.items:
            items_data.append({
                "Description": item.description,
                "Quantity": item.quantity,
                "Unit Price": item.unit_price,
                "Total Price": item.total_price
            })
        st.table(items_data)

def display_comparison_results(comparison: ComparisonResult):
    """Display comparison results in a formatted way."""
    logger.info("Displaying comparison results")
    
    # Create a progress container for comparison steps
    progress_container = st.empty()
    status_container = st.empty()
    
    try:
        # Step 1: Analyzing supplier match
        status_container.info("🔄 Analyzing supplier match...")
        progress_container.progress(20)
        
        # Step 2: Analyzing price matches
        status_container.info("🔄 Analyzing price matches...")
        progress_container.progress(40)
        
        # Step 3: Analyzing service matches
        status_container.info("🔄 Analyzing service matches...")
        progress_container.progress(60)
        
        # Step 4: Generating comparison report
        status_container.info("🔄 Generating comparison report...")
        progress_container.progress(80)
        
        # Overall match status
        if comparison.overall_match:
            logger.info("All checks passed")
            status_container.success("✅ All checks passed! The invoice matches the contract.")
        else:
            logger.warning(f"Some checks failed. Issues: {len(comparison.issues)}")
            status_container.error("❌ Some checks failed. Please review the issues below.")
        
        progress_container.progress(100)
        
        # Display matches
        st.subheader("Match Results")
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.write("Supplier Name")
            if comparison.matches["supplier_name"]:
                st.success("✅ Match")
            else:
                st.error("❌ Mismatch")
        
        with col2:
            st.write("Prices")
            if comparison.matches["prices_match"]:
                st.success("✅ Match")
            else:
                st.error("❌ Mismatch")
        
        with col3:
            st.write("Services")
            if comparison.matches["all_services_in_contract"]:
                st.success("✅ All in contract")
            else:
                st.error("❌ Some services not in contract")
        
        # Display issues if any
        if comparison.issues:
            logger.debug(f"Displaying {len(comparison.issues)} issues")
            st.subheader("Issues Found")
            for issue in comparison.issues:
                if issue["type"] == "supplier_mismatch":
                    st.error(f"Supplier name mismatch: Contract has '{issue['contract_value']}', Invoice has '{issue['invoice_value']}'")
                elif issue["type"] == "price_mismatch":
                    st.error(f"Price mismatch for '{issue['service_name']}': Contract price is {issue['contract_value']}, Invoice price is {issue['invoice_value']}")
                elif issue["type"] == "service_not_in_contract":
                    st.error(f"Service '{issue['service_name']}' is not in the contract")
    finally:
        # Clear the progress indicators after a delay
        import time
        time.sleep(2)
        progress_container.empty()
        status_container.empty()

def process_uploaded_file(uploaded_file, file_extension: str) -> Tuple[Optional[ExtractedDocument], Optional[str]]:
    """Process the uploaded file and return the extracted document or error message."""
    logger.info(f"Processing uploaded file: {uploaded_file.name}")
    
    # Check if we already have the extracted data
    file_key = f"invoice_{uploaded_file.name}"
    if file_key in st.session_state.extracted_data:
        logger.info(f"Using cached data for {uploaded_file.name}")
        cached_doc = st.session_state.extracted_data[file_key]
        logger.info(f"Cached document details: Invoice Number={cached_doc.invoice_number}, Supplier={cached_doc.supplier_name}")
        
        # Check if invoice already exists
        existing_invoice = next((i for i in st.session_state.invoices 
                               if i["name"] == uploaded_file.name), None)
        if existing_invoice:
            logger.info(f"Invoice already exists: {uploaded_file.name}")
            return cached_doc, None
        return cached_doc, None
    
    # Create a progress container
    progress_container = st.empty()
    status_container = st.empty()
    
    try:
        # Step 1: Converting document to image
        status_container.info("🔄 Converting document to image...")
        progress_container.progress(20)
        
        # Process the document
        doc = DocumentProcessor.extract_document_data(
            uploaded_file.getvalue(),
            file_extension
        )
        
        # Store the extracted data
        st.session_state.extracted_data[file_key] = doc
        logger.info(f"Stored extracted data for {uploaded_file.name}")
        
        # Step 2: Document processed successfully
        status_container.success("✅ Document processed successfully!")
        progress_container.progress(100)
        
        logger.info("Successfully processed document")
        return doc, None
    except ValueError as e:
        # Handle verification errors
        status_container.error(f"❌ Verification error: {str(e)}")
        progress_container.progress(0)
        logger.warning(f"Verification error: {str(e)}")
        return None, str(e)
    except Exception as e:
        # Handle other processing errors
        status_container.error(f"❌ Error processing document: {str(e)}")
        progress_container.progress(0)
        logger.error(f"Error processing document: {str(e)}", exc_info=True)
        return None, f"Error processing document: {str(e)}"
    finally:
        # Clear the progress indicators after a delay
        import time
        time.sleep(2)
        progress_container.empty()
        status_container.empty()

def process_contract_file(uploaded_file, file_extension: str) -> Tuple[Optional[Contract], Optional[str]]:
    """Process the uploaded contract file and return the contract or error message."""
    logger.info(f"Processing uploaded contract: {uploaded_file.name}")
    
    # Check if we already have the extracted data
    file_key = f"contract_{uploaded_file.name}"
    if file_key in st.session_state.extracted_data:
        logger.info(f"Using cached data for {uploaded_file.name}")
        doc = st.session_state.extracted_data[file_key]
        logger.info(f"Cached document details: Supplier={doc.supplier_name}")
        
        # Check if contract already exists
        existing_contract = next((c for c in st.session_state.contracts 
                                if c.supplier_name == doc.supplier_name), None)
        if existing_contract:
            logger.info(f"Contract already exists: ID={existing_contract.id}")
            return existing_contract, None
    else:
        # Create a progress container
        progress_container = st.empty()
        status_container = st.empty()
        
        try:
            # Step 1: Converting document to image
            status_container.info("🔄 Converting document to image...")
            progress_container.progress(20)
            
            # Step 2: Extracting document data
            status_container.info("🔄 Extracting document data...")
            progress_container.progress(40)
            
            # Process the document
            doc = DocumentProcessor.extract_document_data(
                uploaded_file.getvalue(),
                file_extension
            )
            
            # Store the extracted data
            st.session_state.extracted_data[file_key] = doc
            logger.info(f"Stored extracted data for {uploaded_file.name}")
            
            # Step 3: Creating contract
            status_container.info("🔄 Creating contract...")
            progress_container.progress(60)
            
            # Step 4: Contract created successfully
            status_container.success("✅ Contract created successfully!")
            progress_container.progress(100)
            
        except Exception as e:
            status_container.error(f"❌ Error processing contract: {str(e)}")
            progress_container.progress(0)
            logger.error(f"Error processing contract: {str(e)}", exc_info=True)
            return None, f"Error processing contract: {str(e)}"
        finally:
            # Clear the progress indicators after a delay
            import time
            time.sleep(2)
            progress_container.empty()
            status_container.empty()
    
    try:
        # Create contract from document
        contract = Contract({
            "id": f"contract-{len(st.session_state.contracts) + 1}",
            "supplier_name": doc.supplier_name,
            "services": [
                {
                    "service_name": item.description,
                    "unit_price": item.unit_price
                }
                for item in doc.items
            ],
            "created_at": doc.issue_date,
            "updated_at": None
        })
        
        # Add contract to session state
        st.session_state.contracts.append(contract)
        logger.info(f"Added contract to session state: ID={contract.id}, Supplier={contract.supplier_name}")
        
        logger.info("Successfully processed contract")
        return contract, None
    except Exception as e:
        logger.error(f"Error creating contract: {str(e)}", exc_info=True)
        return None, f"Error creating contract: {str(e)}"

def compare_documents(contract: Contract, invoice: ExtractedDocument) -> ComparisonResult:
    """Compare a contract with an invoice using cached data."""
    logger.info(f"Comparing contract {contract.id} with invoice")
    
    # Create a progress container for comparison steps
    progress_container = st.empty()
    status_container = st.empty()
    
    try:
        # Step 1: Analyzing supplier match
        status_container.info("🔄 Analyzing supplier match...")
        progress_container.progress(20)
        
        # Step 2: Analyzing price matches
        status_container.info("🔄 Analyzing price matches...")
        progress_container.progress(40)
        
        # Step 3: Analyzing service matches
        status_container.info("🔄 Analyzing service matches...")
        progress_container.progress(60)
        
        # Step 4: Generating comparison report
        status_container.info("🔄 Generating comparison report...")
        progress_container.progress(80)
        
        # Perform the comparison
        comparison = DocumentProcessor.compare_documents(contract, invoice)
        
        # Step 5: Comparison complete
        status_container.success("✅ Comparison complete!")
        progress_container.progress(100)
        
        return comparison
    except Exception as e:
        status_container.error(f"❌ Error during comparison: {str(e)}")
        progress_container.progress(0)
        logger.error(f"Error during comparison: {str(e)}", exc_info=True)
        raise
    finally:
        # Clear the progress indicators after a delay
        import time
        time.sleep(2)
        progress_container.empty()
        status_container.empty()

def main():
    logger.info("Starting Streamlit application")
    st.title("Invoice Validation Tool")
    
    # Add a button to verify state
    if st.sidebar.button("Verify State"):
        verify_state()
    
    # Create tabs for different functionalities
    tab1, tab2, tab3 = st.tabs(["Upload Contract", "Upload Invoices", "Compare Invoices"])
    
    with tab1:
        logger.debug("Initializing Upload Contract tab")
        st.header("Upload Contract")
        st.write("Upload a contract document to use for invoice validation.")
        
        uploaded_file = st.file_uploader(
            "Upload Contract",
            type=['pdf', 'png', 'jpg', 'jpeg'],
            help="Supported formats: PDF, PNG, JPG, JPEG"
        )
        
        if uploaded_file:
            logger.info(f"Contract file uploaded: {uploaded_file.name}")
            # Get file extension
            file_extension = uploaded_file.name.split('.')[-1].lower()
            
            # Process the contract
            contract, error = process_contract_file(uploaded_file, file_extension)
            
            if error:
                logger.error(f"Error processing contract: {error}")
                st.error(error)
            elif contract:
                logger.info("Successfully processed contract")
                st.success("✅ Contract processed successfully!")
                
                # Display contract info
                with st.expander("View Contract Details"):
                    st.json({
                        "Contract ID": contract.id,
                        "Supplier Name": contract.supplier_name,
                        "Services": [
                            {
                                "Service Name": service["service_name"],
                                "Unit Price": service["unit_price"]
                            }
                            for service in contract.services
                        ],
                        "Created At": contract.created_at
                    })
    
    with tab2:
        logger.debug("Initializing Upload Invoices tab")
        st.header("Upload Invoices")
        st.write("Upload one or more invoices for validation.")
        
        uploaded_files = st.file_uploader(
            "Upload Invoices",
            type=['pdf', 'png', 'jpg', 'jpeg'],
            help="Supported formats: PDF, PNG, JPG, JPEG",
            accept_multiple_files=True
        )
        
        if uploaded_files:
            for uploaded_file in uploaded_files:
                logger.info(f"Invoice file uploaded: {uploaded_file.name}")
                # Get file extension
                file_extension = uploaded_file.name.split('.')[-1].lower()
                
                # Check if invoice already exists
                existing_invoice = next((i for i in st.session_state.invoices 
                                      if i["name"] == uploaded_file.name), None)
                if existing_invoice:
                    logger.info(f"Invoice already exists: {uploaded_file.name}")
                    with st.expander(f"View {uploaded_file.name} Details"):
                        display_document_info(existing_invoice["document"])
                    continue
                
                # Process the document
                doc, error = process_uploaded_file(uploaded_file, file_extension)
                
                if error:
                    logger.error(f"Error processing invoice: {error}")
                    st.error(f"Error processing {uploaded_file.name}: {error}")
                elif doc:
                    logger.info("Successfully processed invoice")
                    st.success(f"✅ {uploaded_file.name} processed successfully!")
                    
                    # Add invoice to session state
                    st.session_state.invoices.append({
                        "name": uploaded_file.name,
                        "document": doc
                    })
                    logger.info(f"Added invoice to session state: {uploaded_file.name}")
                    
                    # Display invoice info
                    with st.expander(f"View {uploaded_file.name} Details"):
                        display_document_info(doc)
    
    with tab3:
        logger.debug("Initializing Compare Invoices tab")
        st.header("Compare Invoices with Contract")
        st.write("Select a contract and invoice to compare.")
        
        # Log current state
        logger.info(f"Current state - Contracts: {len(st.session_state.contracts)}, Invoices: {len(st.session_state.invoices)}")
        for i, contract in enumerate(st.session_state.contracts):
            logger.info(f"Contract {i}: ID={contract.id}, Supplier={contract.supplier_name}")
        
        # Contract selection
        if not st.session_state.contracts:
            st.warning("Please upload a contract first.")
        else:
            # Create a list of contract display names
            contract_display_names = [f"{contract.supplier_name} (ID: {contract.id})" 
                                    for contract in st.session_state.contracts]
            
            logger.debug(f"Contract display names: {contract_display_names}")
            
            # Use index-based selection
            selected_contract_idx = st.selectbox(
                "Select Contract",
                options=range(len(st.session_state.contracts)),
                format_func=lambda x: contract_display_names[x]
            )
            
            # Get the selected contract
            selected_contract = st.session_state.contracts[selected_contract_idx]
            logger.debug(f"Selected contract: {selected_contract.id}")
            
            # Invoice selection
            if not st.session_state.invoices:
                st.warning("Please upload invoices first.")
            else:
                # Create a list of invoice display names
                invoice_display_names = [invoice["name"] for invoice in st.session_state.invoices]
                
                logger.debug(f"Invoice display names: {invoice_display_names}")
                
                # Use index-based selection
                selected_invoice_idx = st.selectbox(
                    "Select Invoice",
                    options=range(len(st.session_state.invoices)),
                    format_func=lambda x: invoice_display_names[x]
                )
                
                # Get the selected invoice
                selected_invoice = st.session_state.invoices[selected_invoice_idx]
                logger.debug(f"Selected invoice: {selected_invoice['name']}")
                
                # Compare button
                if st.button("Compare"):
                    logger.info("Starting document comparison")
                    comparison = compare_documents(selected_contract, selected_invoice["document"])
                    display_comparison_results(comparison)

if __name__ == "__main__":
    main() 
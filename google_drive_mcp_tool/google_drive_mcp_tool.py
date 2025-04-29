#!/usr/bin/env python
"""
Google Drive MCP Server - Provides Google Drive document management and editing services via MCP protocol.
"""

import os
import sys
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field
from mcp.server.fastmcp import FastMCP
from mcp.server import Server
from dotenv import load_dotenv
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.routing import Mount, Route
from mcp.server.sse import SseServerTransport
import uvicorn
import logging
import logging.config
import io
import tempfile
from pathlib import Path

# Import configurations
try:
    from config import (
        LOGGING_CONFIG,
        MCP_HOST,
        DRIVE_MCP_PORT
    )
except ImportError:
    # Default configurations if not available
    LOGGING_CONFIG = {
        'version': 1,
        'formatters': {
            'standard': {
                'format': '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            },
        },
        'handlers': {
            'console': {
                'class': 'logging.StreamHandler',
                'level': 'INFO',
                'formatter': 'standard',
                'stream': 'ext://sys.stdout'
            },
            'file': {
                'class': 'logging.FileHandler',
                'level': 'DEBUG',
                'formatter': 'standard',
                'filename': 'gdrive_mcp_server.log',
                'mode': 'a'
            }
        },
        'loggers': {
            'gdrive_mcp_server': {
                'handlers': ['console', 'file'],
                'level': 'DEBUG',
                'propagate': False
            }
        }
    }
    MCP_HOST = "localhost"
    DRIVE_MCP_PORT = 3006

# Import helper
from drive_helper import (
    drive_helper, 
    ensure_authenticated, 
    get_document_content,
    update_document_content,
    get_spreadsheet_content,
    update_spreadsheet_content,
    update_spreadsheet_values,
    get_presentation_content,
    update_presentation_content
)

# Configure logging
logging.config.dictConfig(LOGGING_CONFIG)
logger = logging.getLogger('gdrive_mcp_server')

# Create MCP server
mcp = FastMCP("GoogleDriveTools")

# -------------------------------------------------------------------------
# File Listing Tool
# -------------------------------------------------------------------------

class DriveFilesRequest(BaseModel):
    query: Optional[str] = ""
    max_results: Optional[int] = 10

class DriveFilesResponse(BaseModel):
    files: List[Dict[str, Any]]
    error: Optional[str] = None

@mcp.tool()
async def list_drive_files(request: DriveFilesRequest) -> DriveFilesResponse:
    """
    List files in Google Drive based on the provided query.
    
    Args:
        request: An object containing the search query and max results.
        
    Returns:
        An object containing the files and any error messages.
    """
    try:
        logger.info(f"Listing Google Drive files with query: {request.query}")
        
        # Use helper to get files
        result = drive_helper.list_files(
            query=request.query,
            max_results=request.max_results
        )
        
        if result["error"]:
            logger.error(result["error"])
            return DriveFilesResponse(
                files=[],
                error=result["error"]
            )
        
        logger.info(f"Successfully retrieved {len(result['files'])} files")
        return DriveFilesResponse(
            files=result["files"],
            error=None
        )
        
    except Exception as e:
        error_msg = f"Error in list_drive_files: {str(e)}"
        logger.error(error_msg, exc_info=True)
        return DriveFilesResponse(files=[], error=error_msg)

# -------------------------------------------------------------------------
# File Metadata Tool
# -------------------------------------------------------------------------

class FileMetadataRequest(BaseModel):
    file_id: str

class FileMetadataResponse(BaseModel):
    metadata: Optional[Dict[str, Any]] = None
    error: Optional[str] = None

@mcp.tool()
async def get_file_metadata(request: FileMetadataRequest) -> FileMetadataResponse:
    """
    Get metadata for a specific file in Google Drive.
    
    Args:
        request: An object containing the file ID.
        
    Returns:
        An object containing the file metadata and any error messages.
    """
    try:
        logger.info(f"Getting metadata for file: {request.file_id}")
        
        # Use helper to get file metadata
        result = drive_helper.get_file_metadata(
            file_id=request.file_id
        )
        
        if result["error"]:
            logger.error(result["error"])
            return FileMetadataResponse(
                metadata=None,
                error=result["error"]
            )
        
        logger.info(f"Successfully retrieved metadata for file: {result['metadata'].get('name')}")
        return FileMetadataResponse(
            metadata=result["metadata"],
            error=None
        )
        
    except Exception as e:
        error_msg = f"Error in get_file_metadata: {str(e)}"
        logger.error(error_msg, exc_info=True)
        return FileMetadataResponse(metadata=None, error=error_msg)

# -------------------------------------------------------------------------
# Folder Creation Tool
# -------------------------------------------------------------------------

class CreateFolderRequest(BaseModel):
    name: str
    parent_id: Optional[str] = None

class FolderResponse(BaseModel):
    folder: Optional[Dict[str, Any]] = None
    error: Optional[str] = None

@mcp.tool()
async def create_drive_folder(request: CreateFolderRequest) -> FolderResponse:
    """
    Create a new folder in Google Drive.
    
    Args:
        request: An object containing the folder name and optional parent ID.
        
    Returns:
        An object containing the created folder metadata and any error messages.
    """
    try:
        logger.info(f"Creating folder: {request.name}")
        
        # Use helper to create folder
        result = drive_helper.create_folder(
            name=request.name,
            parent_id=request.parent_id
        )
        
        if result["error"]:
            logger.error(result["error"])
            return FolderResponse(
                folder=None,
                error=result["error"]
            )
        
        logger.info(f"Successfully created folder: {result['folder'].get('name')}")
        return FolderResponse(
            folder=result["folder"],
            error=None
        )
        
    except Exception as e:
        error_msg = f"Error in create_drive_folder: {str(e)}"
        logger.error(error_msg, exc_info=True)
        return FolderResponse(folder=None, error=error_msg)

# -------------------------------------------------------------------------
# Document Creation Tools
# -------------------------------------------------------------------------

class CreateDocumentRequest(BaseModel):
    name: str
    content: Optional[str] = None
    parent_id: Optional[str] = None

class DocumentResponse(BaseModel):
    document: Optional[Dict[str, Any]] = None
    error: Optional[str] = None

@mcp.tool()
async def create_drive_document(request: CreateDocumentRequest) -> DocumentResponse:
    """
    Create a new Google Docs document.
    
    Args:
        request: An object containing the document name, optional content, and optional parent ID.
        
    Returns:
        An object containing the created document metadata and any error messages.
    """
    try:
        logger.info(f"Creating document: {request.name}")
        
        # Use helper to create document
        result = drive_helper.create_document(
            name=request.name,
            content=request.content,
            parent_id=request.parent_id
        )
        
        if result["error"]:
            logger.error(result["error"])
            return DocumentResponse(
                document=None,
                error=result["error"]
            )
        
        logger.info(f"Successfully created document: {result['document'].get('name')}")
        return DocumentResponse(
            document=result["document"],
            error=None
        )
        
    except Exception as e:
        error_msg = f"Error in create_drive_document: {str(e)}"
        logger.error(error_msg, exc_info=True)
        return DocumentResponse(document=None, error=error_msg)

class CreateSpreadsheetRequest(BaseModel):
    name: str
    parent_id: Optional[str] = None

class SpreadsheetResponse(BaseModel):
    spreadsheet: Optional[Dict[str, Any]] = None
    error: Optional[str] = None

@mcp.tool()
async def create_drive_spreadsheet(request: CreateSpreadsheetRequest) -> SpreadsheetResponse:
    """
    Create a new Google Sheets spreadsheet.
    
    Args:
        request: An object containing the spreadsheet name and optional parent ID.
        
    Returns:
        An object containing the created spreadsheet metadata and any error messages.
    """
    try:
        logger.info(f"Creating spreadsheet: {request.name}")
        
        # Use helper to create spreadsheet
        result = drive_helper.create_spreadsheet(
            name=request.name,
            parent_id=request.parent_id
        )
        
        if result["error"]:
            logger.error(result["error"])
            return SpreadsheetResponse(
                spreadsheet=None,
                error=result["error"]
            )
        
        logger.info(f"Successfully created spreadsheet: {result['spreadsheet'].get('name')}")
        return SpreadsheetResponse(
            spreadsheet=result["spreadsheet"],
            error=None
        )
        
    except Exception as e:
        error_msg = f"Error in create_drive_spreadsheet: {str(e)}"
        logger.error(error_msg, exc_info=True)
        return SpreadsheetResponse(spreadsheet=None, error=error_msg)

class CreatePresentationRequest(BaseModel):
    name: str
    parent_id: Optional[str] = None

class PresentationResponse(BaseModel):
    presentation: Optional[Dict[str, Any]] = None
    error: Optional[str] = None

@mcp.tool()
async def create_drive_presentation(request: CreatePresentationRequest) -> PresentationResponse:
    """
    Create a new Google Slides presentation.
    
    Args:
        request: An object containing the presentation name and optional parent ID.
        
    Returns:
        An object containing the created presentation metadata and any error messages.
    """
    try:
        logger.info(f"Creating presentation: {request.name}")
        
        # Use helper to create presentation
        result = drive_helper.create_presentation(
            name=request.name,
            parent_id=request.parent_id
        )
        
        if result["error"]:
            logger.error(result["error"])
            return PresentationResponse(
                presentation=None,
                error=result["error"]
            )
        
        logger.info(f"Successfully created presentation: {result['presentation'].get('name')}")
        return PresentationResponse(
            presentation=result["presentation"],
            error=None
        )
        
    except Exception as e:
        error_msg = f"Error in create_drive_presentation: {str(e)}"
        logger.error(error_msg, exc_info=True)
        return PresentationResponse(presentation=None, error=error_msg)

# -------------------------------------------------------------------------
# File Download Tool
# -------------------------------------------------------------------------

class DownloadFileRequest(BaseModel):
    file_id: str
    export_format: Optional[str] = None

class DownloadFileResponse(BaseModel):
    content: Optional[str] = None  # Base64 encoded content
    mime_type: Optional[str] = None
    file_name: Optional[str] = None
    error: Optional[str] = None

@mcp.tool()
async def download_drive_file(request: DownloadFileRequest) -> DownloadFileResponse:
    """
    Download a file from Google Drive.
    
    Args:
        request: An object containing the file ID and optional export format.
        
    Returns:
        An object containing the file content (base64 encoded), MIME type, and any error messages.
    """
    try:
        logger.info(f"Downloading file: {request.file_id}")
        
        # Use helper to download file
        result = drive_helper.download_file(
            file_id=request.file_id,
            export_format=request.export_format
        )
        
        if result["error"]:
            logger.error(result["error"])
            return DownloadFileResponse(
                content=None,
                mime_type=None,
                file_name=None,
                error=result["error"]
            )
        
        # Convert binary content to base64
        import base64
        content_b64 = base64.b64encode(result["content"]).decode('utf-8')
        
        logger.info(f"Successfully downloaded file: {result.get('file_name')}")
        return DownloadFileResponse(
            content=content_b64,
            mime_type=result["mime_type"],
            file_name=result.get("file_name"),
            error=None
        )
        
    except Exception as e:
        error_msg = f"Error in download_drive_file: {str(e)}"
        logger.error(error_msg, exc_info=True)
        return DownloadFileResponse(
            content=None, 
            mime_type=None,
            file_name=None,
            error=error_msg
        )

# -------------------------------------------------------------------------
# File Delete Tool
# -------------------------------------------------------------------------

class DeleteFileRequest(BaseModel):
    file_id: str

class DeleteFileResponse(BaseModel):
    success: bool
    error: Optional[str] = None

@mcp.tool()
async def delete_drive_file(request: DeleteFileRequest) -> DeleteFileResponse:
    """
    Delete a file from Google Drive.
    
    Args:
        request: An object containing the file ID.
        
    Returns:
        An object indicating success or failure and any error messages.
    """
    try:
        logger.info(f"Deleting file: {request.file_id}")
        
        # Use helper to delete file
        result = drive_helper.delete_file(
            file_id=request.file_id
        )
        
        if result["error"]:
            logger.error(result["error"])
            return DeleteFileResponse(
                success=False,
                error=result["error"]
            )
        
        logger.info(f"Successfully deleted file: {request.file_id}")
        return DeleteFileResponse(
            success=True,
            error=None
        )
        
    except Exception as e:
        error_msg = f"Error in delete_drive_file: {str(e)}"
        logger.error(error_msg, exc_info=True)
        return DeleteFileResponse(success=False, error=error_msg)

# -------------------------------------------------------------------------
# File Sharing Tool
# -------------------------------------------------------------------------

class ShareFileRequest(BaseModel):
    file_id: str
    email: str
    role: Optional[str] = "reader"
    type: Optional[str] = "user"
    notify: Optional[bool] = False

class ShareFileResponse(BaseModel):
    permission: Optional[Dict[str, Any]] = None
    error: Optional[str] = None

@mcp.tool()
async def share_drive_file(request: ShareFileRequest) -> ShareFileResponse:
    """
    Share a file with another user.
    
    Args:
        request: An object containing:
            - file_id: ID of the file to share
            - email: Email address of the user to share with
            - role: Permission role ('reader', 'writer', 'commenter', 'owner')
            - type: Permission type ('user', 'group', 'domain', 'anyone')
            - notify: Whether to send notification email
        
    Returns:
        An object containing the permission data and any error messages.
    """
    try:
        logger.info(f"Sharing file {request.file_id} with {request.email}")
        
        # Use helper to share file
        result = drive_helper.share_file(
            file_id=request.file_id,
            email=request.email,
            role=request.role,
            type=request.type,
            notify=request.notify
        )
        
        if result["error"]:
            logger.error(result["error"])
            return ShareFileResponse(
                permission=None,
                error=result["error"]
            )
        
        logger.info(f"Successfully shared file with {request.email}")
        return ShareFileResponse(
            permission=result["permission"],
            error=None
        )
        
    except Exception as e:
        error_msg = f"Error in share_drive_file: {str(e)}"
        logger.error(error_msg, exc_info=True)
        return ShareFileResponse(permission=None, error=error_msg)

# -------------------------------------------------------------------------
# File Upload Tool
# -------------------------------------------------------------------------

class UploadFileRequest(BaseModel):
    file_path: str
    name: Optional[str] = None
    parent_id: Optional[str] = None
    mime_type: Optional[str] = None
    convert: Optional[bool] = False

class UploadFileResponse(BaseModel):
    file: Optional[Dict[str, Any]] = None
    error: Optional[str] = None

@mcp.tool()
async def upload_file_to_drive(request: UploadFileRequest) -> UploadFileResponse:
    """
    Upload a local file to Google Drive.
    
    Args:
        request: An object containing:
            - file_path: Path to the local file
            - name: Name to give the file in Drive (optional)
            - parent_id: ID of parent folder (optional)
            - mime_type: MIME type of the file (optional)
            - convert: Whether to convert to Google format (optional)
        
    Returns:
        An object containing the uploaded file metadata and any error messages.
    """
    try:
        logger.info(f"Uploading file: {request.file_path}")
        
        # Verify file exists
        if not os.path.exists(request.file_path):
            error_msg = f"File not found: {request.file_path}"
            logger.error(error_msg)
            return UploadFileResponse(file=None, error=error_msg)
        
        # Use helper to upload file
        result = drive_helper.upload_file(
            file_path=request.file_path,
            name=request.name,
            parent_id=request.parent_id,
            mime_type=request.mime_type,
            convert=request.convert
        )
        
        if result["error"]:
            logger.error(result["error"])
            return UploadFileResponse(
                file=None,
                error=result["error"]
            )
        
        logger.info(f"Successfully uploaded file: {result['file'].get('name')}")
        return UploadFileResponse(
            file=result["file"],
            error=None
        )
        
    except Exception as e:
        error_msg = f"Error in upload_file_to_drive: {str(e)}"
        logger.error(error_msg, exc_info=True)
        return UploadFileResponse(file=None, error=error_msg)

# -------------------------------------------------------------------------
# Authentication Tool
# -------------------------------------------------------------------------

class AuthenticationRequest(BaseModel):
    pass  # No parameters needed

class AuthenticationResponse(BaseModel):
    authenticated: bool
    message: str
    error: Optional[str] = None

@mcp.tool()
async def authenticate_drive(request: AuthenticationRequest) -> AuthenticationResponse:
    """
    Authenticate with Google Drive API and establish a connection.
    
    This tool initiates the OAuth flow if needed and validates the connection.
    For new users, it will open a browser window for authentication.
    For returning users with valid credentials, it will use the stored token.
    
    Returns:
        An object containing authentication status and any error messages.
    """
    try:
        logger.info("Manual authentication requested")
        
        # Try to authenticate using helper function
        auth_result = ensure_authenticated()
        
        if auth_result["authenticated"]:
            logger.info(f"Manual authentication successful: {auth_result['message']}")
            return AuthenticationResponse(
                authenticated=True,
                message=auth_result['message'],
                error=None
            )
        else:
            logger.error(f"Manual authentication failed: {auth_result['message']}")
            return AuthenticationResponse(
                authenticated=False,
                message=auth_result['message'],
                error=auth_result['error']
            )
        
    except Exception as e:
        error_msg = f"Error in authenticate_drive: {str(e)}"
        logger.error(error_msg, exc_info=True)
        return AuthenticationResponse(
            authenticated=False,
            message="Unexpected error during authentication",
            error=error_msg
        )

# -------------------------------------------------------------------------
# Document Content Tools
# -------------------------------------------------------------------------

class GetDocumentContentRequest(BaseModel):
    document_id: str

class DocumentContentResponse(BaseModel):
    content: Optional[Dict[str, Any]] = None
    error: Optional[str] = None

@mcp.tool()
async def get_document_content_tool(request: GetDocumentContentRequest) -> DocumentContentResponse:
    """
    Get the full content of a Google Docs document.
    
    This tool retrieves the entire content structure of a Google Docs document,
    including text, formatting, and other elements.
    
    Args:
        request: An object containing the document ID
        
    Returns:
        An object containing the document content and any error messages
    """
    try:
        logger.info(f"Getting content for document: {request.document_id}")
        
        # Use helper to get document content
        result = get_document_content(request.document_id)
        
        if result["error"]:
            logger.error(result["error"])
            return DocumentContentResponse(
                content=None,
                error=result["error"]
            )
        
        logger.info(f"Successfully retrieved document content")
        return DocumentContentResponse(
            content=result["content"],
            error=None
        )
        
    except Exception as e:
        error_msg = f"Error in get_document_content_tool: {str(e)}"
        logger.error(error_msg, exc_info=True)
        return DocumentContentResponse(content=None, error=error_msg)

class UpdateDocumentRequest(BaseModel):
    document_id: str
    requests: List[Dict[str, Any]]

class UpdateDocumentResponse(BaseModel):
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None

@mcp.tool()
async def update_document_content_tool(request: UpdateDocumentRequest) -> UpdateDocumentResponse:
    """
    Update the content of a Google Docs document.
    
    This tool allows you to apply multiple changes to a document in a single batch
    operation. Changes can include inserting text, deleting content, applying styling,
    adding images, and more.
    
    The requests parameter should be a list of operations following the
    Google Docs API batchUpdate format.
    
    Args:
        request: An object containing:
            - document_id: ID of the document to update
            - requests: List of change operations to apply
        
    Returns:
        An object containing the update result and any error messages
    """
    try:
        logger.info(f"Updating content for document: {request.document_id}")
        
        # Use helper to update document content
        result = update_document_content(
            request.document_id,
            request.requests
        )
        
        if result["error"]:
            logger.error(result["error"])
            return UpdateDocumentResponse(
                result=None,
                error=result["error"]
            )
        
        logger.info(f"Successfully updated document content")
        return UpdateDocumentResponse(
            result=result["result"],
            error=None
        )
        
    except Exception as e:
        error_msg = f"Error in update_document_content_tool: {str(e)}"
        logger.error(error_msg, exc_info=True)
        return UpdateDocumentResponse(result=None, error=error_msg)

# -------------------------------------------------------------------------
# Spreadsheet Content Tools
# -------------------------------------------------------------------------

class GetSpreadsheetContentRequest(BaseModel):
    spreadsheet_id: str

class SpreadsheetContentResponse(BaseModel):
    content: Optional[Dict[str, Any]] = None
    error: Optional[str] = None

@mcp.tool()
async def get_spreadsheet_content_tool(request: GetSpreadsheetContentRequest) -> SpreadsheetContentResponse:
    """
    Get the content of a Google Sheets spreadsheet.
    
    This tool retrieves the structure and data of a spreadsheet, including
    sheet names, cell data, and formatting information.
    
    Args:
        request: An object containing the spreadsheet ID
        
    Returns:
        An object containing the spreadsheet content and any error messages
    """
    try:
        logger.info(f"Getting content for spreadsheet: {request.spreadsheet_id}")
        
        # Use helper to get spreadsheet content
        result = get_spreadsheet_content(request.spreadsheet_id)
        
        if result["error"]:
            logger.error(result["error"])
            return SpreadsheetContentResponse(
                content=None,
                error=result["error"]
            )
        
        logger.info(f"Successfully retrieved spreadsheet content")
        return SpreadsheetContentResponse(
            content=result["content"],
            error=None
        )
        
    except Exception as e:
        error_msg = f"Error in get_spreadsheet_content_tool: {str(e)}"
        logger.error(error_msg, exc_info=True)
        return SpreadsheetContentResponse(content=None, error=error_msg)

class UpdateSpreadsheetRequest(BaseModel):
    spreadsheet_id: str
    requests: List[Dict[str, Any]]

class UpdateSpreadsheetResponse(BaseModel):
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None

@mcp.tool()
async def update_spreadsheet_content_tool(request: UpdateSpreadsheetRequest) -> UpdateSpreadsheetResponse:
    """
    Update the structure and formatting of a Google Sheets spreadsheet.
    
    This tool allows you to apply multiple changes to a spreadsheet in a single batch
    operation. Changes can include adding sheets, deleting rows/columns, merging cells,
    changing formats, and more.
    
    The requests parameter should be a list of operations following the
    Google Sheets API batchUpdate format.
    
    Args:
        request: An object containing:
            - spreadsheet_id: ID of the spreadsheet to update
            - requests: List of structural change operations to apply
        
    Returns:
        An object containing the update result and any error messages
    """
    try:
        logger.info(f"Updating content for spreadsheet: {request.spreadsheet_id}")
        
        # Use helper to update spreadsheet content
        result = update_spreadsheet_content(
            request.spreadsheet_id,
            request.requests
        )
        
        if result["error"]:
            logger.error(result["error"])
            return UpdateSpreadsheetResponse(
                result=None,
                error=result["error"]
            )
        
        logger.info(f"Successfully updated spreadsheet content")
        return UpdateSpreadsheetResponse(
            result=result["result"],
            error=None
        )
        
    except Exception as e:
        error_msg = f"Error in update_spreadsheet_content_tool: {str(e)}"
        logger.error(error_msg, exc_info=True)
        return UpdateSpreadsheetResponse(result=None, error=error_msg)

class UpdateSpreadsheetValuesRequest(BaseModel):
    spreadsheet_id: str
    range: str
    values: List[List[Any]]
    input_option: Optional[str] = "USER_ENTERED"

class UpdateSpreadsheetValuesResponse(BaseModel):
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None

@mcp.tool()
async def update_spreadsheet_values_tool(request: UpdateSpreadsheetValuesRequest) -> UpdateSpreadsheetValuesResponse:
    """
    Update cell values in a Google Sheets spreadsheet.
    
    This tool allows you to update the values of cells in a specified range.
    You can use this for data entry, calculations, or populating a sheet.
    
    Args:
        request: An object containing:
            - spreadsheet_id: ID of the spreadsheet to update
            - range: Cell range in A1 notation (e.g., "Sheet1!A1:B5")
            - values: 2D array of values to set
            - input_option: How to interpret the input values ("RAW" or "USER_ENTERED")
        
    Returns:
        An object containing the update result and any error messages
    """
    try:
        logger.info(f"Updating values in spreadsheet: {request.spreadsheet_id}, range: {request.range}")
        
        # Use helper to update spreadsheet values
        result = update_spreadsheet_values(
            request.spreadsheet_id,
            request.range,
            request.values,
            request.input_option
        )
        
        if result["error"]:
            logger.error(result["error"])
            return UpdateSpreadsheetValuesResponse(
                result=None,
                error=result["error"]
            )
        
        logger.info(f"Successfully updated spreadsheet values")
        return UpdateSpreadsheetValuesResponse(
            result=result["result"],
            error=None
        )
        
    except Exception as e:
        error_msg = f"Error in update_spreadsheet_values_tool: {str(e)}"
        logger.error(error_msg, exc_info=True)
        return UpdateSpreadsheetValuesResponse(result=None, error=error_msg)

# -------------------------------------------------------------------------
# Presentation Content Tools
# -------------------------------------------------------------------------

class GetPresentationContentRequest(BaseModel):
    presentation_id: str

class PresentationContentResponse(BaseModel):
    content: Optional[Dict[str, Any]] = None
    error: Optional[str] = None

@mcp.tool()
async def get_presentation_content_tool(request: GetPresentationContentRequest) -> PresentationContentResponse:
    """
    Get the content of a Google Slides presentation.
    
    This tool retrieves the full structure of a presentation, including
    slides, layouts, elements, and text content.
    
    Args:
        request: An object containing the presentation ID
        
    Returns:
        An object containing the presentation content and any error messages
    """
    try:
        logger.info(f"Getting content for presentation: {request.presentation_id}")
        
        # Use helper to get presentation content
        result = get_presentation_content(request.presentation_id)
        
        if result["error"]:
            logger.error(result["error"])
            return PresentationContentResponse(
                content=None,
                error=result["error"]
            )
        
        logger.info(f"Successfully retrieved presentation content")
        return PresentationContentResponse(
            content=result["content"],
            error=None
        )
        
    except Exception as e:
        error_msg = f"Error in get_presentation_content_tool: {str(e)}"
        logger.error(error_msg, exc_info=True)
        return PresentationContentResponse(content=None, error=error_msg)

class UpdatePresentationRequest(BaseModel):
    presentation_id: str
    requests: List[Dict[str, Any]]

class UpdatePresentationResponse(BaseModel):
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None

@mcp.tool()
async def update_presentation_content_tool(request: UpdatePresentationRequest) -> UpdatePresentationResponse:
    """
    Update the content of a Google Slides presentation.
    
    This tool allows you to apply multiple changes to a presentation in a single batch
    operation. Changes can include adding slides, inserting text, adding images,
    updating shapes, and more.
    
    The requests parameter should be a list of operations following the
    Google Slides API batchUpdate format.
    
    Args:
        request: An object containing:
            - presentation_id: ID of the presentation to update
            - requests: List of change operations to apply
        
    Returns:
        An object containing the update result and any error messages
    """
    try:
        logger.info(f"Updating content for presentation: {request.presentation_id}")
        
        # Use helper to update presentation content
        result = update_presentation_content(
            request.presentation_id,
            request.requests
        )
        
        if result["error"]:
            logger.error(result["error"])
            return UpdatePresentationResponse(
                result=None,
                error=result["error"]
            )
        
        logger.info(f"Successfully updated presentation content")
        return UpdatePresentationResponse(
            result=result["result"],
            error=None
        )
        
    except Exception as e:
        error_msg = f"Error in update_presentation_content_tool: {str(e)}"
        logger.error(error_msg, exc_info=True)
        return UpdatePresentationResponse(result=None, error=error_msg)

# -------------------------------------------------------------------------
# File Management Tools (continued)
# -------------------------------------------------------------------------

class MoveFileRequest(BaseModel):
    file_id: str
    destination_folder_id: str
    keep_previous_parents: Optional[bool] = False

class MoveFileResponse(BaseModel):
    file: Optional[Dict[str, Any]] = None
    error: Optional[str] = None

@mcp.tool()
async def move_drive_file(request: MoveFileRequest) -> MoveFileResponse:
    """
    Move a file to a different folder in Google Drive.
    
    This tool moves a file from its current location to a specified destination folder.
    By default, it removes the file from all previous parent folders.
    
    Args:
        request: An object containing:
            - file_id: ID of the file to move
            - destination_folder_id: ID of the destination folder
            - keep_previous_parents: Whether to keep the file in its previous locations (optional, default: False)
        
    Returns:
        An object containing the moved file metadata and any error messages
    """
    try:
        logger.info(f"Moving file {request.file_id} to folder {request.destination_folder_id}")
        
        # Use helper to move file
        result = drive_helper.move_file(
            file_id=request.file_id,
            new_parent_id=request.destination_folder_id,
            remove_parents=not request.keep_previous_parents
        )
        
        if result["error"]:
            logger.error(result["error"])
            return MoveFileResponse(
                file=None,
                error=result["error"]
            )
        
        logger.info(f"Successfully moved file to destination folder")
        return MoveFileResponse(
            file=result["file"],
            error=None
        )
        
    except Exception as e:
        error_msg = f"Error in move_drive_file: {str(e)}"
        logger.error(error_msg, exc_info=True)
        return MoveFileResponse(file=None, error=error_msg)

# -------------------------------------------------------------------------
# Server Setup
# -------------------------------------------------------------------------

def create_starlette_app(mcp_server: Server, *, debug: bool = False) -> Starlette:
    """Create a Starlette app with SSE transport for the MCP server."""
    sse = SseServerTransport("/messages/")

    async def handle_sse(request: Request) -> None:
        async with sse.connect_sse(
            request.scope,
            request.receive,
            request._send,
        ) as (read_stream, write_stream):
            await mcp_server.run(
                read_stream,
                write_stream,
                mcp_server.create_initialization_options(),
            )

    return Starlette(
        debug=debug,
        routes=[
            Route("/sse", endpoint=handle_sse),
            Mount("/messages/", app=sse.handle_post_message),
        ],
    )

def main():
    import argparse

    # Get MCP server instance from FastMCP
    mcp_server = mcp._mcp_server

    parser = argparse.ArgumentParser(description="Google Drive MCP Server")
    parser.add_argument("--port", type=int, default=DRIVE_MCP_PORT, help="Port for server")
    parser.add_argument("--host", type=str, default=MCP_HOST, help="Host for server")
    parser.add_argument("--skip-auth-check", action="store_true", help="Skip authentication check before starting server")
    
    args = parser.parse_args()
    
    # Check authentication before starting the server
    if not args.skip_auth_check:
        logger.info("Checking Google Drive API authentication before starting server")
        
        auth_result = ensure_authenticated()
        
        if auth_result["authenticated"]:
            logger.info(f"Authentication successful: {auth_result['message']}")
        else:
            logger.error(f"Authentication failed: {auth_result['message']}")
            logger.error(f"Error details: {auth_result['error']}")
            
            # Print a user-friendly message
            print("\n" + "="*80)
            print(" AUTHENTICATION ERROR ".center(80, "="))
            print("="*80)
            print(f"\nFailed to authenticate with Google Drive API: {auth_result['message']}")
            print("\nThe server will still start, but Drive-related operations may fail.")
            print("You can try accessing the server and authenticating through API requests.")
            print("\nTo bypass this check next time, use --skip-auth-check\n")
    
    logger.info(f"Starting Google Drive MCP Server on {args.host}:{args.port}")
    
    # Create Starlette app with SSE transport
    starlette_app = create_starlette_app(mcp_server, debug=True)
    
    # Run the server with uvicorn
    uvicorn.run(
        starlette_app,
        host=args.host,
        port=args.port,
    )

if __name__ == "__main__":
    main()

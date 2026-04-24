# TODO - have the creae users function check for existing users and update them instead of creating duplicates. This will require defining a unique key (probably email) and using upsert with that key instead of just inserting new documents. For now it just creates new documents for each folder and response, which can lead to duplicates if run multiple times with the same data.
# TODO - create an update users function that can take in any data.
"""Azure gateway utilities.

Provides a lightweight `AzureGateway` class for verifying Typeform
signatures and storing form responses into MongoDB. The class defers
creating a MongoDB client until a store operation is requested so it
is safe to import in environments where MongoDB is not configured.
"""

import hmac
import hashlib
import os
from typing import Optional, Dict, Any, List
from pymongo import MongoClient
import base64
from pathlib import Path
import os

try:
	import pandas as pd
except Exception:
	pd = None


class AzureGateway: 
	"""Gateway for handling Typeform webhook verification and storage.
    Also includes utilities for adding folders and users to MongoDB and sending Twilio messages.
	Parameters
	- mongo_uri: MongoDB connection string. If not provided, read
	  from `MONGODB_URI` environment variable.
	- db_name: database name (default: 'RemixDB')
	- collection_name: collection name (default: 'TypeformResponses')
	- typeform_secret: webhook secret. If not provided, read from
	  `TYPEFORM_WEBHOOK_SECRET` environment variable.
	"""

	def __init__(
		self,
		mongo_uri: Optional[str] = None,
		db_name: str = "RemixDB",
		collection_name: str = "TypeformResponses",
		typeform_secret: Optional[str] = None,
	) -> None:
		self.mongo_uri = mongo_uri or os.getenv("MONGODB_URI")
		self.db_name = db_name
		self.collection_name = collection_name
		self.typeform_secret = typeform_secret or os.getenv("TYPEFORM_WEBHOOK_SECRET", "")
		self._client: Optional[MongoClient] = None

	def _get_collection(self):
		if not self.mongo_uri:
			return None
		if not self._client:
			self._client = MongoClient(self.mongo_uri)
		return self._client[self.db_name][self.collection_name]

	def _get_collection_by_name(self, collection_name: str):
		if not self.mongo_uri:
			return None
		if not self._client:
			self._client = MongoClient(self.mongo_uri)
		return self._client[self.db_name][collection_name]

	def verify_typeform_signature(self, request_body: bytes, signature_header: str) -> bool:
		"""Verify the Typeform webhook signature.

		Returns True if verification passes or if no secret is configured.
		Returns False when a secret is configured but the signature does not match.
		"""
		if not self.typeform_secret:
			# No secret configured; cannot verify — treat as allowed.
			return True
		if not signature_header:
			return False
		expected = "sha256=" + hmac.new(
			self.typeform_secret.encode(), request_body, hashlib.sha256
		).hexdigest()
		return signature_header == expected

	def store_typeform_response(self, form_response: Dict[str, Any]) -> Optional[Dict[str, Any]]:
		"""Store or upsert a Typeform response document into MongoDB.

		Returns a small summary dict on success, or None if MongoDB is not configured.
		"""
		collection = self._get_collection()
		if collection is None:
			return None

		result = collection.update_one(
			{"response_id": form_response.get("response_id")}, {"$set": form_response}, upsert=True
		)

		return {
			"matched_count": getattr(result, "matched_count", None),
			"modified_count": getattr(result, "modified_count", None),
			"upserted_id": str(getattr(result, "upserted_id", None)) if getattr(result, "upserted_id", None) else None,
		}

	def add_folder_to_mongodb(self, folder_path: str, person_name: Optional[str] = None, users_collection: str = "Users") -> Optional[Any]:
		"""Recursively add files from a folder to the Users collection.

		Returns the inserted document id or None if DB not configured.
		"""
		collection = self._get_collection_by_name(users_collection)
		if collection is None:
			return None

		folder_path = Path(folder_path)
		if not folder_path.exists():
			raise FileNotFoundError(f"Folder not found: {folder_path}")

		if person_name is None:
			person_name = folder_path.name

		folder_data = {"name": person_name, "folder_source": str(folder_path), "files": []}

		for root, dirs, files in os.walk(folder_path):
			for filename in files:
				file_path = Path(root) / filename
				relative_path = file_path.relative_to(folder_path)

				file_info = {
					"filename": filename,
					"relative_path": str(relative_path),
					"full_path": str(file_path),
					"file_type": file_path.suffix.lower(),
				}

				try:
					if file_path.suffix.lower() in [".jpg", ".jpeg", ".png", ".gif", ".webp", ".bmp"]:
						with open(file_path, "rb") as img:
							img_data = base64.b64encode(img.read()).decode("utf-8")
							file_info["content_type"] = "image"
							file_info["data_base64"] = img_data
							file_info["size"] = len(img_data)
					elif file_path.suffix.lower() in [".txt", ".md", ".csv", ".json"]:
						with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
							content = f.read()
							file_info["content_type"] = "text"
							file_info["content"] = content
							file_info["size"] = len(content)
					elif file_path.suffix.lower() == ".pdf":
						with open(file_path, "rb") as pdf:
							pdf_data = base64.b64encode(pdf.read()).decode("utf-8")
							file_info["content_type"] = "pdf"
							file_info["data_base64"] = pdf_data
							file_info["size"] = len(pdf_data)
					else:
						file_info["content_type"] = "binary"
						file_info["size"] = file_path.stat().st_size
				except Exception as e:
					file_info["error"] = str(e)
					file_info["content_type"] = "error"

				folder_data["files"].append(file_info)

		result = collection.insert_one(folder_data)
		return result.inserted_id

	def create_users_combined(self, responses_df, person_folders_dict: Dict[str, str], users_collection: str = "Users") -> Optional[List[Any]]:
		"""Create combined user documents from responses DataFrame and folders dict.

		`responses_df` may be a pandas DataFrame or a list of dicts. Returns list of inserted ids.
		
		The `person_folders_dict` should map person names to folder paths. The function will attempt to match person names in the responses with the folder names, and combine the data into a single user document for each person. It will also handle any remaining responses that don't have a matching folder.
		
		As of now the function will create duplicate users if they are already in the database; it does not attempt to check for existing users or update them. It simply inserts new documents for each folder and response.
		"""
		collection = self._get_collection_by_name(users_collection)
		if collection is None:
			return None

		# Accept list-of-dicts as well
		if pd is None and not hasattr(responses_df, "iterrows"):
			raise RuntimeError("pandas is required to pass DataFrame; or pass a list of dicts")

		def read_folder_files(folder_path: str):
			folder = Path(folder_path)
			files_list = []
			if not folder.exists():
				return files_list
			for root, dirs, files in os.walk(folder):
				for filename in files:
					file_path = Path(root) / filename
					relative_path = file_path.relative_to(folder)
					file_info = {"filename": filename, "relative_path": str(relative_path), "full_path": str(file_path), "file_type": file_path.suffix.lower()}
					try:
						if file_path.suffix.lower() in [".jpg", ".jpeg", ".png", ".gif", ".webp", ".bmp"]:
							with open(file_path, "rb") as img:
								img_data = base64.b64encode(img.read()).decode("utf-8")
								file_info["content_type"] = "image"
								file_info["data_base64"] = img_data
								file_info["size"] = len(img_data)
						elif file_path.suffix.lower() in [".txt", ".md", ".csv", ".json"]:
							with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
								content = f.read()
								file_info["content_type"] = "text"
								file_info["content"] = content
								file_info["size"] = len(content)
						elif file_path.suffix.lower() == ".pdf":
							with open(file_path, "rb") as pdf:
								pdf_data = base64.b64encode(pdf.read()).decode("utf-8")
								file_info["content_type"] = "pdf"
								file_info["data_base64"] = pdf_data
								file_info["size"] = len(pdf_data)
						else:
							file_info["content_type"] = "binary"
							file_info["size"] = file_path.stat().st_size
					except Exception as e:
						file_info["error"] = str(e)
						file_info["content_type"] = "error"
					files_list.append(file_info)
			return files_list

		inserted_ids = []
		processed_responses = set()

		# If responses_df is list of dicts, convert to iterable with index
		if pd is not None and hasattr(responses_df, "iterrows"):
			iterator = responses_df.iterrows()
		else:
			# list of dicts
			iterator = enumerate(responses_df)

		# First pass: folders
		for person_name, folder_path in person_folders_dict.items():
			user_document = {"name": person_name, "email": None, "phone": None, "form_responses": None, "session_info": None}
			# Find matching response
			if pd is not None and hasattr(responses_df, "iterrows"):
				matches = responses_df[responses_df['name'].str.lower() == person_name.lower()]
				if not matches.empty:
					response_dict = matches.iloc[0].to_dict()
					# mark processed by index
					processed_responses.add(matches.index[0])
					user_document['email'] = response_dict.get('email')
					user_document['phone'] = response_dict.get('phone')
					excluded_fields = {'name', 'email', 'phone'}
					user_document['form_responses'] = {k: v for k, v in response_dict.items() if k not in excluded_fields}
			else:
				# list of dicts: try to find matching name
				for idx, rd in enumerate(responses_df):
					if str(rd.get('name','')).lower() == person_name.lower():
						response_dict = rd
						processed_responses.add(idx)
						user_document['email'] = response_dict.get('email')
						user_document['phone'] = response_dict.get('phone')
						excluded_fields = {'name', 'email', 'phone'}
						user_document['form_responses'] = {k: v for k, v in response_dict.items() if k not in excluded_fields}
						break

			folder_files = read_folder_files(folder_path)
			user_document['session_info'] = {'files': folder_files, 'folder_source': str(folder_path), 'file_count': len(folder_files)}
			result = collection.insert_one(user_document)
			inserted_ids.append(result.inserted_id)

		# Second pass: remaining responses without folders
		if pd is not None and hasattr(responses_df, "iterrows"):
			for idx, row in responses_df.iterrows():
				if idx in processed_responses:
					continue
				response_dict = row.to_dict()
				person_name = response_dict.get('name')
				user_document = {"name": person_name, "email": response_dict.get('email'), "phone": response_dict.get('phone'), 'form_responses': {k: v for k, v in response_dict.items() if k not in {'name','email','phone'}}, 'session_info': {'files': [], 'folder_source': None, 'file_count': 0}}
				result = collection.insert_one(user_document)
				inserted_ids.append(result.inserted_id)
		else:
			for idx, rd in enumerate(responses_df):
				if idx in processed_responses:
					continue
				person_name = rd.get('name')
				user_document = {"name": person_name, "email": rd.get('email'), "phone": rd.get('phone'), 'form_responses': {k: v for k, v in rd.items() if k not in {'name','email','phone'}}, 'session_info': {'files': [], 'folder_source': None, 'file_count': 0}}
				result = collection.insert_one(user_document)
				inserted_ids.append(result.inserted_id)

		return inserted_ids

	def send_and_record_twilio_message(self, account_sid: str, auth_token: str, from_number: str, to_number: str, body: str, messages_collection: str = "Messages") -> Dict[str, Any]:
		"""Send a Twilio message and record it into the Messages collection.

		Returns the inserted document and Twilio SID/status where available.
		"""
		collection = self._get_collection_by_name(messages_collection)
		if collection is None:
			raise RuntimeError("MongoDB not configured")

		try:
			from twilio.rest import Client
		except Exception as e:
			raise RuntimeError("twilio package required to send messages") from e

		twilio_client = Client(account_sid, auth_token)
		try:
			message = twilio_client.messages.create(body=body, from_=from_number, to=to_number)
			message_data = {
				"sid": getattr(message, 'sid', None),
				"body": getattr(message, 'body', None),
				"from_": getattr(message, 'from_', None),
				"to": getattr(message, 'to', None),
				"status": getattr(message, 'status', None),
				"date_created": getattr(message, 'date_created', None),
				"date_sent": getattr(message, 'date_sent', None),
				"date_updated": getattr(message, 'date_updated', None),
				"error": None,
			}
			insert_res = collection.insert_one(message_data)

			# try fetch updated status
			try:
				time_msg = twilio_client.messages(message.sid).fetch()
				collection.update_one({"sid": message.sid}, {"$set": {"status": getattr(time_msg, 'status', None), "date_updated": getattr(time_msg, 'date_updated', None), "error": getattr(time_msg, 'error_message', None)}})
			except Exception:
				pass

			return {"inserted_id": insert_res.inserted_id, "sid": message_data.get('sid'), "status": message_data.get('status')}

		except Exception as e:
			# store failure
			doc = {"sid": None, "body": body, "from_": from_number, "to": to_number, "status": "send_failed", "error": str(e)}
			insert_res = collection.insert_one(doc)
			return {"inserted_id": insert_res.inserted_id, "sid": None, "status": "send_failed", "error": str(e)}


__all__ = ["AzureGateway"]
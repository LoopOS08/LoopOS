import httpx
import json
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
from app.services.integrations.base import BaseIntegration, NormalizedArtifact
from app.models.integration import SourceTool
from app.models.artifact import ArtifactType
import logging

logger = logging.getLogger(__name__)


class HubSpotIntegration(BaseIntegration):
    """
    HubSpot Integration following three-phase pattern:
    1. OAuth 2.0 Authentication
    2. Webhooks (primary) + CRM Search API (polling)
    3. Normalization to standard artifact format
    """
    
    @property
    def source_tool(self) -> SourceTool:
        return SourceTool.HUBSPOT
    
    @property
    def webhook_events(self) -> List[str]:
        return [
            'deal.propertyChange',
            'contact.propertyChange',
            'contact.creation',
            'note.creation',
            'company.propertyChange',
            'company.creation'
        ]
    
    def __init__(self, company_id: str, credentials_encrypted: str, settings: Dict[str, Any] = None):
        super().__init__(company_id, credentials_encrypted, settings)
        self.base_url = "https://api.hubapi.com"
        self._http_client = None
    
    async def _get_http_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client"""
        if self._http_client is None:
            self._http_client = httpx.AsyncClient(timeout=30.0)
        return self._http_client
    
    async def authenticate(self) -> bool:
        """Validate HubSpot credentials using a test API call"""
        try:
            credentials = await self.get_credentials()
            access_token = credentials.get('access_token')
            
            if not access_token:
                logger.error("No access token in credentials")
                return False
            
            client = await self._get_http_client()
            response = await client.get(
                f"{self.base_url}/crm/v3/objects/contacts?limit=1",
                headers={"Authorization": f"Bearer {access_token}"}
            )
            
            if response.status_code == 200:
                logger.info("HubSpot authentication successful")
                return True
            else:
                logger.error(f"HubSpot authentication failed: {response.status_code}")
                return False
            
        except Exception as e:
            logger.error(f"HubSpot authentication failed: {e}")
            return False
    
    async def process_webhook(self, event_data: Dict[str, Any]) -> Optional[NormalizedArtifact]:
        """
        Process HubSpot webhook
        Handles: deal.propertyChange, contact.propertyChange, contact.creation, note.creation
        """
        try:
            # HubSpot webhook format
            event_type = event_data.get('eventTypeId', '')
            
            if 'deal' in event_type:
                return await self._process_deal_event(event_data)
            elif 'contact' in event_type:
                return await self._process_contact_event(event_data)
            elif 'note' in event_type:
                return await self._process_note_event(event_data)
            elif 'company' in event_type:
                return await self._process_company_event(event_data)
            else:
                logger.debug(f"Unhandled HubSpot webhook type: {event_type}")
                return None
            
        except Exception as e:
            logger.error(f"Failed to process HubSpot webhook: {e}")
            return None
    
    async def _process_deal_event(self, event_data: Dict[str, Any]) -> Optional[NormalizedArtifact]:
        """Process HubSpot deal event"""
        try:
            object_id = event_data.get('objectId')
            change_source = event_data.get('changeSource', {})
            event_type = event_data.get('eventTypeId', '')
            
            # Fetch full deal details
            deal_data = await self._fetch_deal_details(object_id)
            
            if not deal_data:
                return None
            
            # Extract deal information
            deal_properties = deal_data.get('properties', {})
            deal_name = deal_properties.get('dealname', 'unknown')
            deal_stage = deal_properties.get('dealstage', 'unknown')
            deal_amount = deal_properties.get('amount', '0')
            deal_close_date = deal_properties.get('closedate', '')
            
            # Owner information
            owner_id = deal_properties.get('hubspot_owner_id')
            owner_name = 'Unknown'
            owner_email = ''
            
            if owner_id:
                owner_info = await self._fetch_owner_details(owner_id)
                if owner_info:
                    owner_name = owner_info.get('firstName', '') + ' ' + owner_info.get('lastName', '')
                    owner_email = owner_info.get('email', '')
            
            # Company information
            company_id = deal_properties.get('associatedcompanyids', '').split(';')[0] if deal_properties.get('associatedcompanyids') else None
            company_name = 'unknown'
            
            if company_id:
                company_data = await self._fetch_company_details(company_id)
                if company_data:
                    company_name = company_data.get('properties', {}).get('name', 'unknown')
            
            # Build normalized content
            action = 'updated' if 'propertyChange' in event_type else 'created'
            normalized_content = (
                f"Deal {action}: {deal_name} in {company_name}\n"
                f"Stage: {deal_stage}, Amount: ${deal_amount}\n"
                f"Owner: {owner_name}\n"
                f"Close Date: {deal_close_date or 'not set'}"
            )
            
            # Build metadata
            metadata = {
                'deal_id': object_id,
                'deal_name': deal_name,
                'deal_stage': deal_stage,
                'deal_amount': deal_amount,
                'close_date': deal_close_date,
                'company_name': company_name,
                'owner_name': owner_name,
                'probability': deal_properties.get('probability', '0'),
                'created_at': deal_properties.get('createdate'),
                'updated_at': deal_properties.get('hs_lastmodifieddate')
            }
            
            return NormalizedArtifact(
                company_id=self.company_id,
                source_tool=self.source_tool,
                artifact_type=ArtifactType.DEAL,
                external_id=object_id,
                content=normalized_content,
                author=owner_name,
                author_email=owner_email,
                source_created_at=datetime.fromisoformat(deal_properties.get('createdate', '').replace('Z', '+00:00')),
                metadata=metadata
            )
            
        except Exception as e:
            logger.error(f"Failed to process HubSpot deal event: {e}")
            return None
    
    async def _process_contact_event(self, event_data: Dict[str, Any]) -> Optional[NormalizedArtifact]:
        """Process HubSpot contact event"""
        try:
            object_id = event_data.get('objectId')
            event_type = event_data.get('eventTypeId', '')
            
            # Fetch full contact details
            contact_data = await self._fetch_contact_details(object_id)
            
            if not contact_data:
                return None
            
            # Extract contact information
            contact_properties = contact_data.get('properties', {})
            first_name = contact_properties.get('firstname', '')
            last_name = contact_properties.get('lastname', '')
            email = contact_properties.get('email', '')
            company = contact_properties.get('company', '')
            
            full_name = f"{first_name} {last_name}".strip() or 'Unknown'
            
            # Build normalized content
            action = 'updated' if 'propertyChange' in event_type else 'created'
            normalized_content = (
                f"Contact {action}: {full_name} ({email})\n"
                f"Company: {company or 'not set'}"
            )
            
            # Build metadata
            metadata = {
                'contact_id': object_id,
                'first_name': first_name,
                'last_name': last_name,
                'email': email,
                'company': company,
                'phone': contact_properties.get('phone'),
                'lifecycle_stage': contact_properties.get('lifecyclestage'),
                'created_at': contact_properties.get('createdate'),
                'updated_at': contact_properties.get('hs_lastmodifieddate')
            }
            
            return NormalizedArtifact(
                company_id=self.company_id,
                source_tool=self.source_tool,
                artifact_type=ArtifactType.MESSAGE,
                external_id=object_id,
                content=normalized_content,
                author=full_name,
                author_email=email,
                source_created_at=datetime.fromisoformat(contact_properties.get('createdate', '').replace('Z', '+00:00')),
                metadata=metadata
            )
            
        except Exception as e:
            logger.error(f"Failed to process HubSpot contact event: {e}")
            return None
    
    async def _process_note_event(self, event_data: Dict[str, Any]) -> Optional[NormalizedArtifact]:
        """Process HubSpot note event"""
        try:
            object_id = event_data.get('objectId')
            
            # Fetch full note details
            note_data = await self._fetch_note_details(object_id)
            
            if not note_data:
                return None
            
            # Extract note information
            note_properties = note_data.get('properties', {})
            note_content = note_properties.get('hs_note_body', '')
            
            # Owner information
            owner_id = note_properties.get('hubspot_owner_id')
            owner_name = 'Unknown'
            owner_email = ''
            
            if owner_id:
                owner_info = await self._fetch_owner_details(owner_id)
                if owner_info:
                    owner_name = owner_info.get('firstName', '') + ' ' + owner_info.get('lastName', '')
                    owner_email = owner_info.get('email', '')
            
            # Associated contact information
            associations = note_data.get('associations', {})
            contact_associations = associations.get('contacts', {}).get('results', [])
            
            contact_name = 'unknown'
            if contact_associations:
                contact_id = contact_associations[0].get('id')
                contact_data = await self._fetch_contact_details(contact_id)
                if contact_data:
                    contact_props = contact_data.get('properties', {})
                    contact_name = f"{contact_props.get('firstname', '')} {contact_props.get('lastname', '')}".strip()
            
            # Build normalized content
            normalized_content = (
                f"Note by {owner_name} on {contact_name}:\n"
                f"{note_content}"
            )
            
            # Build metadata
            metadata = {
                'note_id': object_id,
                'note_content': note_content,
                'owner_name': owner_name,
                'contact_name': contact_name,
                'created_at': note_properties.get('hs_created_at'),
                'updated_at': note_properties.get('hs_lastmodifieddate')
            }
            
            return NormalizedArtifact(
                company_id=self.company_id,
                source_tool=self.source_tool,
                artifact_type=ArtifactType.MESSAGE,
                external_id=object_id,
                content=normalized_content,
                author=owner_name,
                author_email=owner_email,
                source_created_at=datetime.fromisoformat(note_properties.get('hs_created_at', '').replace('Z', '+00:00')),
                metadata=metadata
            )
            
        except Exception as e:
            logger.error(f"Failed to process HubSpot note event: {e}")
            return None
    
    async def _process_company_event(self, event_data: Dict[str, Any]) -> Optional[NormalizedArtifact]:
        """Process HubSpot company event"""
        try:
            object_id = event_data.get('objectId')
            event_type = event_data.get('eventTypeId', '')
            
            # Fetch full company details
            company_data = await self._fetch_company_details(object_id)
            
            if not company_data:
                return None
            
            # Extract company information
            company_properties = company_data.get('properties', {})
            company_name = company_properties.get('name', 'unknown')
            domain = company_properties.get('domain', '')
            industry = company_properties.get('industry', '')
            
            # Build normalized content
            action = 'updated' if 'propertyChange' in event_type else 'created'
            normalized_content = (
                f"Company {action}: {company_name}\n"
                f"Domain: {domain or 'not set'}\n"
                f"Industry: {industry or 'not set'}"
            )
            
            # Build metadata
            metadata = {
                'company_id': object_id,
                'company_name': company_name,
                'domain': domain,
                'industry': industry,
                'number_of_employees': company_properties.get('numberofemployees'),
                'annual_revenue': company_properties.get('annualrevenue'),
                'created_at': company_properties.get('createdate'),
                'updated_at': company_properties.get('hs_lastmodifieddate')
            }
            
            return NormalizedArtifact(
                company_id=self.company_id,
                source_tool=self.source_tool,
                artifact_type=ArtifactType.MESSAGE,
                external_id=object_id,
                content=normalized_content,
                author='System',
                author_email='',
                source_created_at=datetime.fromisoformat(company_properties.get('createdate', '').replace('Z', '+00:00')),
                metadata=metadata
            )
            
        except Exception as e:
            logger.error(f"Failed to process HubSpot company event: {e}")
            return None
    
    async def _fetch_deal_details(self, deal_id: str) -> Optional[Dict[str, Any]]:
        """Fetch full deal details from HubSpot API"""
        try:
            credentials = await self.get_credentials()
            access_token = credentials.get('access_token')
            
            client = await self._get_http_client()
            response = await client.get(
                f"{self.base_url}/crm/v3/objects/deals/{deal_id}",
                headers={"Authorization": f"Bearer {access_token}"}
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                logger.warning(f"Failed to fetch deal {deal_id}: {response.status_code}")
                return None
                
        except Exception as e:
            logger.error(f"Error fetching deal details: {e}")
            return None
    
    async def _fetch_contact_details(self, contact_id: str) -> Optional[Dict[str, Any]]:
        """Fetch full contact details from HubSpot API"""
        try:
            credentials = await self.get_credentials()
            access_token = credentials.get('access_token')
            
            client = await self._get_http_client()
            response = await client.get(
                f"{self.base_url}/crm/v3/objects/contacts/{contact_id}",
                headers={"Authorization": f"Bearer {access_token}"}
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                logger.warning(f"Failed to fetch contact {contact_id}: {response.status_code}")
                return None
                
        except Exception as e:
            logger.error(f"Error fetching contact details: {e}")
            return None
    
    async def _fetch_note_details(self, note_id: str) -> Optional[Dict[str, Any]]:
        """Fetch full note details from HubSpot API"""
        try:
            credentials = await self.get_credentials()
            access_token = credentials.get('access_token')
            
            client = await self._get_http_client()
            response = await client.get(
                f"{self.base_url}/crm/v3/objects/notes/{note_id}",
                headers={"Authorization": f"Bearer {access_token}"}
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                logger.warning(f"Failed to fetch note {note_id}: {response.status_code}")
                return None
                
        except Exception as e:
            logger.error(f"Error fetching note details: {e}")
            return None
    
    async def _fetch_company_details(self, company_id: str) -> Optional[Dict[str, Any]]:
        """Fetch full company details from HubSpot API"""
        try:
            credentials = await self.get_credentials()
            access_token = credentials.get('access_token')
            
            client = await self._get_http_client()
            response = await client.get(
                f"{self.base_url}/crm/v3/objects/companies/{company_id}",
                headers={"Authorization": f"Bearer {access_token}"}
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                logger.warning(f"Failed to fetch company {company_id}: {response.status_code}")
                return None
                
        except Exception as e:
            logger.error(f"Error fetching company details: {e}")
            return None
    
    async def _fetch_owner_details(self, owner_id: str) -> Optional[Dict[str, Any]]:
        """Fetch owner details from HubSpot API"""
        try:
            credentials = await self.get_credentials()
            access_token = credentials.get('access_token')
            
            client = await self._get_http_client()
            response = await client.get(
                f"{self.base_url}/crm/v3/owners/{owner_id}",
                headers={"Authorization": f"Bearer {access_token}"}
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                logger.warning(f"Failed to fetch owner {owner_id}: {response.status_code}")
                return None
                
        except Exception as e:
            logger.error(f"Error fetching owner details: {e}")
            return None
    
    async def poll_data(self, since: Optional[datetime] = None) -> List[NormalizedArtifact]:
        """
        Poll for missed data using HubSpot CRM Search API
        Also used for hourly sync of deals modified in last 60 minutes
        """
        try:
            credentials = await self.get_credentials()
            access_token = credentials.get('access_token')
            
            client = await self._get_http_client()
            
            # Calculate time filter
            if not since:
                since = datetime.utcnow() - timedelta(hours=1)
            
            # Search for recently modified deals
            deal_search_query = {
                "filterGroups": [
                    {
                        "filters": [
                            {
                                "propertyName": "hs_lastmodifieddate",
                                "operator": "GTE",
                                "value": since.isoformat()
                            }
                        ]
                    }
                ],
                "properties": [
                    "dealname",
                    "dealstage",
                    "amount",
                    "closedate",
                    "hubspot_owner_id",
                    "associatedcompanyids",
                    "probability",
                    "createdate",
                    "hs_lastmodifieddate"
                ],
                "limit": 100
            }
            
            deal_response = await client.post(
                f"{self.base_url}/crm/v3/objects/deals/search",
                headers={
                    "Authorization": f"Bearer {access_token}",
                    "Content-Type": "application/json"
                },
                json=deal_search_query
            )
            
            artifacts = []
            
            if deal_response.status_code == 200:
                deal_data = deal_response.json()
                deals = deal_data.get('results', [])
                
                for deal in deals:
                    event_data = {
                        'eventTypeId': 'deal.propertyChange',
                        'objectId': deal.get('id')
                    }
                    
                    artifact = await self._process_deal_event(event_data)
                    if artifact:
                        artifacts.append(artifact)
            
            # Search for recently modified contacts
            contact_search_query = {
                "filterGroups": [
                    {
                        "filters": [
                            {
                                "propertyName": "hs_lastmodifieddate",
                                "operator": "GTE",
                                "value": since.isoformat()
                            }
                        ]
                    }
                ],
                "properties": [
                    "firstname",
                    "lastname",
                    "email",
                    "company",
                    "phone",
                    "lifecyclestage",
                    "createdate",
                    "hs_lastmodifieddate"
                ],
                "limit": 100
            }
            
            contact_response = await client.post(
                f"{self.base_url}/crm/v3/objects/contacts/search",
                headers={
                    "Authorization": f"Bearer {access_token}",
                    "Content-Type": "application/json"
                },
                json=contact_search_query
            )
            
            if contact_response.status_code == 200:
                contact_data = contact_response.json()
                contacts = contact_data.get('results', [])
                
                for contact in contacts:
                    event_data = {
                        'eventTypeId': 'contact.propertyChange',
                        'objectId': contact.get('id')
                    }
                    
                    artifact = await self._process_contact_event(event_data)
                    if artifact:
                        artifacts.append(artifact)
            
            logger.info(f"Polled {len(artifacts)} artifacts from HubSpot")
            return artifacts
            
        except Exception as e:
            logger.error(f"HubSpot data polling failed: {e}")
            return []
    
    def normalize_event(self, raw_event: Dict[str, Any]) -> NormalizedArtifact:
        """
        Normalize raw HubSpot event to standard artifact format
        This is a synchronous version used for testing
        """
        # For async operations, use process_webhook instead
        raise NotImplementedError("Use process_webhook for async normalization")
    
    def get_oauth_url(self, redirect_uri: str) -> str:
        """Generate HubSpot OAuth URL"""
        from app.core.config import settings
        client_id = settings.HUBSPOT_CLIENT_ID or self.settings.get('hubspot_client_id')
        scopes = "crm.objects.deals.read crm.objects.contacts.read crm.objects.companies.read crm.objects.notes.read crm.timeline.events.read"
        
        return (
            f"https://app.hubspot.com/oauth/authorize"
            f"?client_id={client_id}"
            f"&redirect_uri={redirect_uri}"
            f"&scope={scopes}"
            f"&response_type=code"
        )
    
    async def exchange_code_for_credentials(self, code: str, redirect_uri: str) -> Dict[str, Any]:
        """Exchange OAuth code for access tokens"""
        try:
            from app.core.config import settings
            client_id = settings.HUBSPOT_CLIENT_ID or self.settings.get('hubspot_client_id')
            client_secret = settings.HUBSPOT_CLIENT_SECRET or self.settings.get('hubspot_client_secret')
            
            client = await self._get_http_client()
            response = await client.post(
                "https://api.hubapi.com/oauth/v1/token",
                data={
                    "client_id": client_id,
                    "client_secret": client_secret,
                    "code": code,
                    "redirect_uri": redirect_uri,
                    "grant_type": "authorization_code"
                }
            )
            
            data = response.json()
            
            if 'error' in data:
                raise Exception(f"OAuth exchange failed: {data.get('error')}")
            
            credentials = {
                'access_token': data.get('access_token'),
                'refresh_token': data.get('refresh_token'),
                'token_type': data.get('token_type'),
                'expires_in': data.get('expires_in')
            }
            
            logger.info("Successfully exchanged OAuth code for HubSpot")
            return credentials
            
        except Exception as e:
            logger.error(f"HubSpot OAuth exchange failed: {e}")
            raise
    
    async def refresh_credentials(self) -> bool:
        """Refresh HubSpot access token using refresh token"""
        try:
            from app.core.config import settings
            credentials = await self.get_credentials()
            refresh_token = credentials.get('refresh_token')
            
            if not refresh_token:
                logger.warning("No refresh token available")
                return False
            
            client_id = settings.HUBSPOT_CLIENT_ID or self.settings.get('hubspot_client_id')
            client_secret = settings.HUBSPOT_CLIENT_SECRET or self.settings.get('hubspot_client_secret')
            
            client = await self._get_http_client()
            response = await client.post(
                "https://api.hubapi.com/oauth/v1/token",
                data={
                    "client_id": client_id,
                    "client_secret": client_secret,
                    "refresh_token": refresh_token,
                    "grant_type": "refresh_token"
                }
            )
            
            data = response.json()
            
            if 'error' in data:
                logger.error(f"Token refresh failed: {data.get('error')}")
                return False
            
            # Update credentials with new access token
            credentials['access_token'] = data.get('access_token')
            credentials['expires_in'] = data.get('expires_in')
            
            # Re-encrypt and store updated credentials
            self._credentials = credentials
            # Note: In production, you'd update the database here
            
            logger.info("Successfully refreshed HubSpot credentials")
            return True
            
        except Exception as e:
            logger.error(f"HubSpot credential refresh failed: {e}")
            return False
    
    async def close(self):
        """Close HTTP client"""
        if self._http_client:
            await self._http_client.aclose()

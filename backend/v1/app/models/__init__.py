# import every model so they're all registered on Base.metadata before create_all / mapper configuration
from app.models.base import Base
from app.models.user import User, UserRole
from app.models.facility import Facility
from app.models.building import Building
from app.models.floor import Floor
from app.models.seat import Seat
from app.models.incident import Incident, IncidentCategory, IncidentPriority, IncidentStatus
from app.models.incident_note import IncidentNote
from app.models.incident_status_history import IncidentStatusHistory
from app.models.engineer_profile import EngineerProfile

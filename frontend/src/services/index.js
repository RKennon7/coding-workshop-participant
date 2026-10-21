import apiClient from '../api/client.js';
import { createResource } from './resourceService.js';

export const facilitiesService = createResource('/facilities');
export const buildingsService = createResource('/buildings');
export const floorsService = createResource('/floors');
export const seatsService = createResource('/seats');
export const incidentsService = createResource('/incidents');
export const engineersService = createResource('/engineers');

export const usersService = createResource('/users');

// public: a new user sets their password for the account an admin created for their email
export const registerAccount = (data) => apiClient.post('/auth/register', data).then((res) => res.data);

// notes are nested under their incident
export const incidentNotesService = (incidentId) => createResource(`/incidents/${incidentId}/notes`);

// status change trail for one incident, oldest first
export const fetchIncidentHistory = (incidentId) => apiClient.get(`/incidents/${incidentId}/history`).then((res) => res.data);

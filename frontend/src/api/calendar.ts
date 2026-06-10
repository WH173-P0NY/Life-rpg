import type {
  CalendarEvent,
  CalendarEventPayload,
  CalendarEventType,
  CalendarRecurrenceFrequency
} from "../types/calendar";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "";

type RawCalendarEvent = {
  id: number;
  title: string;
  description: string;
  start_at: string;
  end_at: string;
  all_day: boolean;
  location: string;
  event_type: CalendarEventType;
  source_type: string;
  source_id: number | null;
  recurrence_frequency: CalendarRecurrenceFrequency;
  recurrence_until: string | null;
  recurrence_group: string | null;
  recurrence_index: number;
  created_at: string;
  updated_at: string;
};

type RawCalendarEventsResponse = {
  events: RawCalendarEvent[];
};

type RawCalendarEventResponse = {
  event: RawCalendarEvent;
  events_created?: number;
};

function getCookie(name: string): string {
  const cookie = document.cookie
    .split("; ")
    .find((row) => row.startsWith(`${name}=`));

  return cookie ? decodeURIComponent(cookie.split("=")[1] ?? "") : "";
}

async function requestJson<TResponse>(
  path: string,
  init: RequestInit = {}
): Promise<TResponse> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    credentials: "include",
    headers: {
      Accept: "application/json",
      ...(init.body ? { "Content-Type": "application/json" } : {}),
      ...init.headers
    },
    ...init
  });

  if (!response.ok) {
    throw new Error(`Request failed: ${response.status} ${response.statusText}`);
  }

  return response.json() as Promise<TResponse>;
}

function transformCalendarEvent(raw: RawCalendarEvent): CalendarEvent {
  return {
    id: String(raw.id),
    title: raw.title,
    description: raw.description,
    startAt: raw.start_at,
    endAt: raw.end_at,
    allDay: raw.all_day,
    location: raw.location,
    eventType: raw.event_type,
    sourceType: raw.source_type,
    sourceId: raw.source_id === null ? null : String(raw.source_id),
    recurrenceFrequency: raw.recurrence_frequency,
    recurrenceUntil: raw.recurrence_until,
    recurrenceGroup: raw.recurrence_group,
    recurrenceIndex: raw.recurrence_index,
    createdAt: raw.created_at,
    updatedAt: raw.updated_at
  };
}

export async function fetchCalendarEvents(params?: {
  startAt?: string;
  endAt?: string;
}): Promise<CalendarEvent[]> {
  const searchParams = new URLSearchParams();
  if (params?.startAt) {
    searchParams.set("start", params.startAt);
  }
  if (params?.endAt) {
    searchParams.set("end", params.endAt);
  }

  const query = searchParams.toString();
  const raw = await requestJson<RawCalendarEventsResponse>(
    `/api/calendar/events/${query ? `?${query}` : ""}`
  );
  return raw.events.map(transformCalendarEvent);
}

export async function createCalendarEvent(payload: CalendarEventPayload): Promise<CalendarEvent> {
  const raw = await requestJson<RawCalendarEventResponse>("/api/calendar/events/", {
    method: "POST",
    headers: {
      "X-CSRFToken": getCookie("csrftoken")
    },
    body: JSON.stringify({
      title: payload.title,
      description: payload.description,
      start_at: payload.startAt,
      end_at: payload.endAt,
      all_day: payload.allDay,
      location: payload.location,
      event_type: payload.eventType,
      recurrence_frequency: payload.recurrenceFrequency,
      recurrence_until: payload.recurrenceUntil
    })
  });
  return transformCalendarEvent(raw.event);
}

export async function deleteCalendarEvent(eventId: string): Promise<void> {
  const response = await fetch(`${API_BASE_URL}/api/calendar/events/${eventId}/`, {
    credentials: "include",
    method: "DELETE",
    headers: {
      "X-CSRFToken": getCookie("csrftoken")
    }
  });

  if (!response.ok) {
    throw new Error(`Request failed: ${response.status} ${response.statusText}`);
  }
}

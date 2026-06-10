export type CalendarEventType = "personal" | "work" | "rpg" | "health" | "finance";
export type CalendarRecurrenceFrequency = "none" | "daily" | "weekly" | "monthly";

export interface CalendarEvent {
  id: string;
  title: string;
  description: string;
  startAt: string;
  endAt: string;
  allDay: boolean;
  location: string;
  eventType: CalendarEventType;
  sourceType: string;
  sourceId: string | null;
  recurrenceFrequency: CalendarRecurrenceFrequency;
  recurrenceUntil: string | null;
  recurrenceGroup: string | null;
  recurrenceIndex: number;
  createdAt: string;
  updatedAt: string;
}

export interface CalendarEventPayload {
  title: string;
  description?: string;
  startAt: string;
  endAt: string;
  allDay?: boolean;
  location?: string;
  eventType?: CalendarEventType;
  recurrenceFrequency?: CalendarRecurrenceFrequency;
  recurrenceUntil?: string | null;
}

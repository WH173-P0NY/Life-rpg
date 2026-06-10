import {
  CalendarPlus,
  ChevronLeft,
  ChevronRight,
  Clock,
  MapPin,
  Repeat,
  Trash2
} from "lucide-react";
import type { FormEvent } from "react";
import { useEffect, useMemo, useState } from "react";

import {
  createCalendarEvent,
  deleteCalendarEvent,
  fetchCalendarEvents
} from "../api/calendar";
import { useI18n } from "../i18n";
import type {
  CalendarEvent,
  CalendarEventType,
  CalendarRecurrenceFrequency
} from "../types/calendar";

interface CalendarViewProps {
  isApiReady: boolean;
}

const eventTypes: CalendarEventType[] = ["personal", "work", "rpg", "health", "finance"];
const recurrenceFrequencies: CalendarRecurrenceFrequency[] = [
  "daily",
  "weekly",
  "monthly"
];

function pad(value: number): string {
  return String(value).padStart(2, "0");
}

function dateKey(date: Date): string {
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}`;
}

function dateFromKey(value: string): Date {
  const [year, month, day] = value.split("-").map(Number);
  return new Date(year, month - 1, day);
}

function monthLabel(date: Date, locale: string): string {
  return new Intl.DateTimeFormat(locale, {
    month: "long",
    year: "numeric"
  }).format(date);
}

function weekdayLabels(locale: string): string[] {
  const monday = new Date(2026, 0, 5);
  const formatter = new Intl.DateTimeFormat(locale, { weekday: "short" });
  return Array.from({ length: 7 }, (_, index) => {
    const date = new Date(monday);
    date.setDate(monday.getDate() + index);
    return formatter.format(date);
  });
}

function addMonths(date: Date, amount: number): Date {
  return new Date(date.getFullYear(), date.getMonth() + amount, 1);
}

function monthGrid(monthDate: Date): Date[] {
  const firstDay = new Date(monthDate.getFullYear(), monthDate.getMonth(), 1);
  const lastDay = new Date(monthDate.getFullYear(), monthDate.getMonth() + 1, 0);
  const firstWeekday = (firstDay.getDay() + 6) % 7;
  const lastWeekday = (lastDay.getDay() + 6) % 7;
  const start = new Date(firstDay);
  start.setDate(firstDay.getDate() - firstWeekday);
  const end = new Date(lastDay);
  end.setDate(lastDay.getDate() + (6 - lastWeekday));

  const days: Date[] = [];
  const cursor = new Date(start);
  while (cursor <= end) {
    days.push(new Date(cursor));
    cursor.setDate(cursor.getDate() + 1);
  }
  return days;
}

function eventTimeLabel(event: CalendarEvent, allDayLabel: string): string {
  const start = new Date(event.startAt);
  const end = new Date(event.endAt);
  const spansMultipleDays = dateKey(start) !== dateKey(end);
  if (spansMultipleDays) {
    const dateFormatter = new Intl.DateTimeFormat("en", {
      month: "short",
      day: "2-digit"
    });
    return `${dateFormatter.format(start)} - ${dateFormatter.format(end)}`;
  }
  if (event.allDay) {
    return allDayLabel;
  }
  const formatter = new Intl.DateTimeFormat("en", {
    hour: "2-digit",
    minute: "2-digit"
  });
  return `${formatter.format(new Date(event.startAt))} - ${formatter.format(new Date(event.endAt))}`;
}

function eventDayKeys(event: CalendarEvent): string[] {
  const start = new Date(event.startAt);
  const end = new Date(event.endAt);
  start.setHours(0, 0, 0, 0);
  end.setHours(0, 0, 0, 0);

  const keys: string[] = [];
  const cursor = new Date(start);
  while (cursor <= end) {
    keys.push(dateKey(cursor));
    cursor.setDate(cursor.getDate() + 1);
  }
  return keys;
}

function recurrenceLabel(event: CalendarEvent, seriesLabel: string): string | null {
  if (event.recurrenceFrequency === "none") {
    return null;
  }
  return `${event.recurrenceFrequency} ${seriesLabel}`;
}

export function CalendarView({ isApiReady }: CalendarViewProps) {
  const { t } = useI18n();
  const todayKey = dateKey(new Date());
  const calendarLocale = t("calendar.monthLocale");
  const [monthDate, setMonthDate] = useState(() => new Date());
  const [selectedDate, setSelectedDate] = useState(todayKey);
  const [events, setEvents] = useState<CalendarEvent[]>([]);
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [location, setLocation] = useState("");
  const [eventType, setEventType] = useState<CalendarEventType>("personal");
  const [startTime, setStartTime] = useState("09:00");
  const [endTime, setEndTime] = useState("10:00");
  const [endDate, setEndDate] = useState(todayKey);
  const [allDay, setAllDay] = useState(false);
  const [repeatEnabled, setRepeatEnabled] = useState(false);
  const [recurrenceFrequency, setRecurrenceFrequency] =
    useState<CalendarRecurrenceFrequency>("weekly");
  const [recurrenceUntil, setRecurrenceUntil] = useState(todayKey);
  const [isSaving, setIsSaving] = useState(false);
  const [status, setStatus] = useState<string | null>(null);

  const days = useMemo(() => monthGrid(monthDate), [monthDate]);
  const localizedWeekdayLabels = useMemo(
    () => weekdayLabels(calendarLocale),
    [calendarLocale]
  );
  const rangeStart = `${dateKey(days[0])}T00:00`;
  const rangeEnd = `${dateKey(days[days.length - 1])}T23:59`;

  const eventsByDay = useMemo(() => {
    const grouped = new Map<string, CalendarEvent[]>();
    for (const event of events) {
      for (const key of eventDayKeys(event)) {
        grouped.set(key, [...(grouped.get(key) ?? []), event]);
      }
    }
    return grouped;
  }, [events]);

  const selectedEvents = eventsByDay.get(selectedDate) ?? [];

  async function refreshEvents() {
    if (!isApiReady) {
      setEvents([]);
      return;
    }

    const nextEvents = await fetchCalendarEvents({
      startAt: rangeStart,
      endAt: rangeEnd
    });
    setEvents(nextEvents);
  }

  useEffect(() => {
    void refreshEvents().catch(() => setStatus(t("calendar.apiUnavailable")));
  }, [isApiReady, rangeStart, rangeEnd]);

  useEffect(() => {
    if (endDate < selectedDate) {
      setEndDate(selectedDate);
    }
    if (recurrenceUntil < selectedDate) {
      setRecurrenceUntil(selectedDate);
    }
  }, [selectedDate, endDate, recurrenceUntil]);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!isApiReady) {
      setStatus(t("calendar.apiRequired"));
      return;
    }
    if (!title.trim()) {
      setStatus(t("calendar.titleRequired"));
      return;
    }
    if (endDate < selectedDate) {
      setStatus(t("calendar.endBeforeStart"));
      return;
    }
    if (repeatEnabled && recurrenceUntil < selectedDate) {
      setStatus(t("calendar.repeatBeforeStart"));
      return;
    }

    setIsSaving(true);
    setStatus(null);

    try {
      await createCalendarEvent({
        title: title.trim(),
        description: description.trim(),
        location: location.trim(),
        eventType,
        allDay,
        startAt: `${selectedDate}T${allDay ? "00:00" : startTime}`,
        endAt: `${endDate}T${allDay ? "23:59" : endTime}`,
        recurrenceFrequency: repeatEnabled ? recurrenceFrequency : "none",
        recurrenceUntil: repeatEnabled ? recurrenceUntil : null
      });
      setTitle("");
      setDescription("");
      setLocation("");
      setEndDate(selectedDate);
      setRepeatEnabled(false);
      setRecurrenceFrequency("weekly");
      setRecurrenceUntil(selectedDate);
      setStatus(repeatEnabled ? t("calendar.recurringEventSaved") : t("calendar.eventSaved"));
      await refreshEvents();
    } catch (error) {
      setStatus(error instanceof Error ? error.message : t("calendar.apiUnavailable"));
    } finally {
      setIsSaving(false);
    }
  }

  async function handleDelete(eventId: string) {
    if (!isApiReady) {
      setStatus(t("calendar.apiRequired"));
      return;
    }

    try {
      await deleteCalendarEvent(eventId);
      setStatus(t("calendar.eventDeleted"));
      await refreshEvents();
    } catch (error) {
      setStatus(error instanceof Error ? error.message : t("calendar.apiUnavailable"));
    }
  }

  return (
    <section className="grid gap-4 xl:grid-cols-[1.45fr_0.75fr]">
      <article className="panel p-4">
        <div className="section-heading">
          <div>
              <p className="eyebrow">{t("common.calendar")}</p>
              <h2>{monthLabel(monthDate, calendarLocale)}</h2>
            </div>
          <span>{events.length} {t("calendar.events")}</span>
        </div>

        <div className="mt-4 flex flex-wrap items-center gap-2">
          <button className="icon-button" onClick={() => setMonthDate(addMonths(monthDate, -1))} type="button">
            <ChevronLeft size={17} />
          </button>
          <button
            className="rounded-lg border border-xp/40 bg-xp/10 px-3 py-2 text-sm font-semibold text-xp transition hover:bg-xp/15"
            onClick={() => {
              const today = new Date();
              const key = dateKey(today);
              setMonthDate(today);
              setSelectedDate(key);
              setEndDate(key);
              setRecurrenceUntil(key);
            }}
            type="button"
          >
            {t("calendar.today")}
          </button>
          <button className="icon-button" onClick={() => setMonthDate(addMonths(monthDate, 1))} type="button">
            <ChevronRight size={17} />
          </button>
        </div>

        <div className="mt-5 grid grid-cols-7 gap-2 text-center text-xs font-semibold uppercase tracking-[0.16em] text-zinc-500">
          {localizedWeekdayLabels.map((label) => (
            <div key={label}>{label}</div>
          ))}
        </div>

        <div className="mt-2 grid grid-cols-7 gap-2">
          {days.map((day) => {
            const key = dateKey(day);
            const dayEvents = eventsByDay.get(key) ?? [];
            const isSelected = key === selectedDate;
            const isToday = key === todayKey;
            const isCurrentMonth = day.getMonth() === monthDate.getMonth();

            return (
              <button
                className={`min-h-28 rounded-lg border p-2 text-left transition ${
                  isSelected
                    ? "border-xp/50 bg-xp/10"
                    : "border-white/10 bg-white/[0.03] hover:border-xp/30"
                } ${isCurrentMonth ? "" : "opacity-45"}`}
                key={key}
                onClick={() => setSelectedDate(key)}
                type="button"
              >
                <div className="flex items-center justify-between">
                  <span className={`text-sm font-semibold ${isToday ? "text-xp" : "text-zinc-100"}`}>
                    {day.getDate()}
                  </span>
                  {dayEvents.length ? (
                    <span className="rounded-md border border-white/10 px-1.5 py-0.5 text-[11px] text-zinc-500">
                      {dayEvents.length}
                    </span>
                  ) : null}
                </div>
                <div className="mt-2 space-y-1">
                  {dayEvents.slice(0, 2).map((event) => (
                    <div
                      className="truncate rounded-md bg-xp/10 px-2 py-1 text-[11px] font-medium text-xp"
                      key={event.id}
                    >
                      {event.title}
                    </div>
                  ))}
                  {dayEvents.length > 2 ? (
                    <p className="text-[11px] text-zinc-500">+{dayEvents.length - 2} {t("calendar.more")}</p>
                  ) : null}
                </div>
              </button>
            );
          })}
        </div>
      </article>

      <aside className="space-y-4">
        <article className="panel p-4">
          <div className="section-heading">
            <div>
              <p className="eyebrow">{t("calendar.plan")}</p>
              <h2>{selectedDate}</h2>
            </div>
            <span>{selectedEvents.length}</span>
          </div>

          <form className="mt-4 space-y-3" onSubmit={handleSubmit}>
            <input
              className="field-control mt-0"
              disabled={!isApiReady || isSaving}
              onChange={(event) => setTitle(event.target.value)}
              placeholder={t("calendar.eventTitle")}
              value={title}
            />
            <textarea
              className="field-control mt-0 min-h-20 resize-none"
              disabled={!isApiReady || isSaving}
              onChange={(event) => setDescription(event.target.value)}
              placeholder={t("calendar.description")}
              value={description}
            />
            <input
              className="field-control mt-0"
              disabled={!isApiReady || isSaving}
              onChange={(event) => setLocation(event.target.value)}
              placeholder={t("calendar.location")}
              value={location}
            />
            <select
              className="field-control mt-0"
              disabled={!isApiReady || isSaving}
              onChange={(event) => setEventType(event.target.value as CalendarEventType)}
              value={eventType}
            >
              {eventTypes.map((type) => (
                <option key={type} value={type}>
                  {t(`calendar.type.${type}`)}
                </option>
              ))}
            </select>
            <div className="grid grid-cols-2 gap-2">
              <label className="field-label text-xs">
                {t("calendar.startDate")}
                <input
                  className="field-control mt-1"
                  disabled={!isApiReady || isSaving}
                  onChange={(event) => {
                    const nextDate = event.target.value;
                    if (!nextDate) {
                      return;
                    }
                    setSelectedDate(nextDate);
                    setMonthDate(dateFromKey(nextDate));
                    if (endDate < nextDate) {
                      setEndDate(nextDate);
                    }
                    if (recurrenceUntil < nextDate) {
                      setRecurrenceUntil(nextDate);
                    }
                  }}
                  type="date"
                  value={selectedDate}
                />
              </label>
              <label className="field-label text-xs">
                {t("calendar.endDate")}
                <input
                  className="field-control mt-1"
                  disabled={!isApiReady || isSaving}
                  min={selectedDate}
                  onChange={(event) => setEndDate(event.target.value)}
                  type="date"
                  value={endDate}
                />
              </label>
            </div>
            <label className="flex items-center gap-2 text-sm text-zinc-400">
              <input
                checked={allDay}
                disabled={!isApiReady || isSaving}
                onChange={(event) => setAllDay(event.target.checked)}
                type="checkbox"
              />
              {t("calendar.allDay")}
            </label>
            <div className="grid grid-cols-2 gap-2">
              <input
                className="field-control mt-0"
                disabled={!isApiReady || isSaving || allDay}
                onChange={(event) => setStartTime(event.target.value)}
                type="time"
                value={startTime}
              />
              <input
                className="field-control mt-0"
                disabled={!isApiReady || isSaving || allDay}
                onChange={(event) => setEndTime(event.target.value)}
                type="time"
                value={endTime}
              />
            </div>
            <label className="flex items-center gap-2 rounded-lg border border-white/10 bg-white/[0.03] px-3 py-2 text-sm text-zinc-400">
              <input
                checked={repeatEnabled}
                disabled={!isApiReady || isSaving}
                onChange={(event) => setRepeatEnabled(event.target.checked)}
                type="checkbox"
              />
              {t("calendar.repeat")}
            </label>
            {repeatEnabled ? (
              <div className="grid grid-cols-[1fr_1fr] gap-2">
                <select
                  className="field-control mt-0"
                  disabled={!isApiReady || isSaving}
                  onChange={(event) =>
                    setRecurrenceFrequency(event.target.value as CalendarRecurrenceFrequency)
                  }
                  value={recurrenceFrequency}
                >
                  {recurrenceFrequencies.map((frequency) => (
                    <option key={frequency} value={frequency}>
                      {t(`calendar.frequency.${frequency}`)}
                    </option>
                  ))}
                </select>
                <label className="field-label text-xs">
                  {t("calendar.repeatUntil")}
                  <input
                    className="field-control mt-1"
                    disabled={!isApiReady || isSaving}
                    min={selectedDate}
                    onChange={(event) => setRecurrenceUntil(event.target.value)}
                    type="date"
                    value={recurrenceUntil}
                  />
                </label>
              </div>
            ) : null}
            <button className="primary-button inline-flex items-center justify-center gap-2" disabled={!isApiReady || isSaving || !title.trim()} type="submit">
              <CalendarPlus size={16} />
              {isSaving ? t("common.saving") : t("calendar.addEvent")}
            </button>
          </form>

          {status ? <p className="mt-3 text-sm text-zinc-500">{status}</p> : null}
        </article>

        <article className="panel p-4">
          <div className="section-heading">
            <div>
              <p className="eyebrow">{t("calendar.schedule")}</p>
              <h2>{t("calendar.selectedDay")}</h2>
            </div>
            <span>{selectedEvents.length}</span>
          </div>

          <div className="mt-4 space-y-3">
            {selectedEvents.map((event) => (
              <div className="rounded-lg border border-white/10 bg-white/[0.03] p-3" key={event.id}>
                <div className="flex items-start justify-between gap-3">
                  <div className="min-w-0">
                    <p className="truncate text-sm font-semibold text-zinc-100">{event.title}</p>
                    <p className="mt-1 inline-flex items-center gap-2 text-xs text-zinc-500">
                      <Clock size={13} />
                      {eventTimeLabel(event, t("calendar.allDayLabel"))}
                    </p>
                  </div>
                  <button
                    aria-label={`Delete ${event.title}`}
                    className="icon-button h-8 w-8"
                    onClick={() => void handleDelete(event.id)}
                    type="button"
                  >
                    <Trash2 size={14} />
                  </button>
                </div>
                {event.location ? (
                  <p className="mt-2 inline-flex items-center gap-2 text-xs text-zinc-500">
                    <MapPin size={13} />
                    {event.location}
                  </p>
                ) : null}
                {event.description ? (
                  <p className="mt-2 text-sm leading-6 text-zinc-400">{event.description}</p>
                ) : null}
                {recurrenceLabel(event, t("calendar.recurringSeries")) ? (
                  <p className="mt-2 inline-flex items-center gap-2 text-xs text-zinc-500">
                    <Repeat size={13} />
                    {recurrenceLabel(event, t("calendar.recurringSeries"))}
                  </p>
                ) : null}
              </div>
            ))}

            {selectedEvents.length === 0 ? (
              <p className="rounded-lg border border-white/10 bg-white/[0.03] p-4 text-sm text-zinc-500">
                {t("calendar.noEvents")}
              </p>
            ) : null}
          </div>
        </article>
      </aside>
    </section>
  );
}

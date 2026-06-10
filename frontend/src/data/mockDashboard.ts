import type { DashboardResponse } from "../types/dashboard";

export const mockDashboard: DashboardResponse = {
  hero: {
    name: "Username",
    title: "The journey shapes the legend.",
    level: 23,
    rank: "Gold",
    totalXp: 2340,
    currentLevelXp: 2340,
    nextLevelXp: 3500,
    progressPercent: 67
  },
  resources: [
    {
      id: "energy",
      name: "Energy",
      value: 78,
      maxValue: 100,
      progressPercent: 78
    },
    {
      id: "focus",
      name: "Focus",
      value: 68,
      maxValue: 100,
      progressPercent: 68
    },
    {
      id: "stamina",
      name: "Stamina",
      value: 6,
      maxValue: 10,
      progressPercent: 60
    }
  ],
  attributes: [
    {
      id: "strength",
      name: "Strength",
      description: "Physical performance",
      value: 78,
      progressPercent: 78,
      growth: 2
    },
    {
      id: "intelligence",
      name: "Intelligence",
      description: "Learning and knowledge",
      value: 62,
      progressPercent: 62,
      growth: 1
    },
    {
      id: "discipline",
      name: "Discipline",
      description: "Consistency and execution",
      value: 71,
      progressPercent: 71,
      growth: 3
    },
    {
      id: "charisma",
      name: "Charisma",
      description: "Communication and relationships",
      value: 59,
      progressPercent: 59,
      growth: 0
    },
    {
      id: "creativity",
      name: "Creativity",
      description: "Creation and innovation",
      value: 64,
      progressPercent: 64,
      growth: 1
    },
    {
      id: "wealth",
      name: "Wealth",
      description: "Financial growth",
      value: 48,
      progressPercent: 48,
      growth: 1
    }
  ],
  dailyQuests: [
    {
      id: "workout",
      title: "Workout 30 minutes",
      progressValue: 20,
      targetValue: 30,
      progressPercent: 67,
      unit: "min",
      completed: false,
      reward: {
        xp: 25,
        skillIds: ["fitness"]
      },
      rewardSkills: [{ id: "fitness", name: "Fitness", xp: 25 }]
    },
    {
      id: "read",
      title: "Read 20 minutes",
      progressValue: 20,
      targetValue: 20,
      progressPercent: 100,
      unit: "min",
      completed: true,
      reward: {
        xp: 20,
        skillIds: ["reading", "learning"]
      },
      rewardSkills: [
        { id: "reading", name: "Reading", xp: 10 },
        { id: "learning", name: "Learning", xp: 10 }
      ]
    },
    {
      id: "study-ai",
      title: "Study AI",
      progressValue: 35,
      targetValue: 45,
      progressPercent: 78,
      unit: "min",
      completed: false,
      reward: {
        xp: 35,
        skillIds: ["learning", "research"]
      },
      rewardSkills: [
        { id: "learning", name: "Learning", xp: 20 },
        { id: "research", name: "Research", xp: 15 }
      ]
    }
  ],
  habits: [
    {
      id: "sleep",
      name: "Sleep before midnight",
      checked: true,
      completedToday: true,
      streakDays: 14
    },
    {
      id: "water",
      name: "Hydration",
      checked: true,
      completedToday: true,
      streakDays: 8
    },
    {
      id: "walk",
      name: "Walk 8000 steps",
      checked: false,
      completedToday: false,
      streakDays: 3
    },
    {
      id: "journal",
      name: "Reflection journal",
      checked: true,
      completedToday: true,
      streakDays: 5
    }
  ],
  habitsSummary: {
    completed: 3,
    total: 4,
    streakDays: 14
  },
  activeChallenge: {
    id: "no-sugar",
    title: "30 Days No Sugar",
    day: 14,
    totalDays: 30,
    progressPercent: 47,
    rewardLabel: "Epic Willpower Badge"
  },
  skills: [
    {
      id: "programming",
      name: "Programming",
      level: 16,
      xp: 820,
      progressPercent: 74
    },
    {
      id: "fitness",
      name: "Fitness",
      level: 12,
      xp: 540,
      progressPercent: 48
    },
    {
      id: "learning",
      name: "Learning",
      level: 19,
      xp: 1060,
      progressPercent: 83
    }
  ],
  statuses: [
    {
      id: "sleep",
      name: "Sleep",
      value: 85,
      maxValue: 100,
      progressPercent: 85
    },
    {
      id: "nutrition",
      name: "Nutrition",
      value: 72,
      maxValue: 100,
      progressPercent: 72
    },
    {
      id: "entertainment",
      name: "Entertainment",
      value: 44,
      maxValue: 100,
      progressPercent: 44
    }
  ],
  weeklyProgress: {
    xp: 850,
    quests: 12,
    levels: 4,
    points: [
      { label: "Mon", xp: 90, minutes: 70 },
      { label: "Tue", xp: 120, minutes: 95 },
      { label: "Wed", xp: 110, minutes: 80 },
      { label: "Thu", xp: 160, minutes: 130 },
      { label: "Fri", xp: 140, minutes: 100 },
      { label: "Sat", xp: 190, minutes: 150 },
      { label: "Sun", xp: 40, minutes: 30 }
    ]
  },
  achievements: [
    {
      id: "early-riser",
      title: "Early Riser",
      rarity: "common",
      unlockedAtLabel: "3 days ago"
    },
    {
      id: "book-worm",
      title: "Book Worm",
      rarity: "rare",
      unlockedAtLabel: "5 days ago"
    },
    {
      id: "unstoppable",
      title: "Unstoppable",
      rarity: "epic",
      unlockedAtLabel: "7 day streak"
    }
  ],
  journalEntries: [
    {
      id: "today",
      title: "Daily Chronicle",
      content: "Today I completed every quest that mattered.",
      excerpt: "Today I completed every quest that mattered.",
      entryType: "manual",
      mood: "focused",
      entryDate: "2026-06-10",
      createdAt: "2026-06-10T21:30:00+02:00",
      createdAtLabel: "Today"
    }
  ],
  activityDefinitions: [
    {
      id: "programming",
      name: "Programming",
      defaultMinutes: 30
    },
    {
      id: "reading",
      name: "Reading",
      defaultMinutes: 20
    },
    {
      id: "fitness",
      name: "Fitness",
      defaultMinutes: 30
    }
  ]
};

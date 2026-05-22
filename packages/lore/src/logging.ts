type LogLevel = "debug" | "info" | "warn" | "error";

interface LogEntry {
  timestamp: string;
  level: LogLevel;
  subsystem: string;
  message: string;
  data?: Record<string, unknown>;
}

const logLevelPriority: Record<LogLevel, number> = {
  debug: 0,
  info: 1,
  warn: 2,
  error: 3,
};

function getMinLevel(): LogLevel {
  const envLevel = process.env.LOG_LEVEL?.toLowerCase() as LogLevel | undefined;
  return envLevel && logLevelPriority[envLevel] !== undefined ? envLevel : "info";
}

function formatEntry(entry: LogEntry): string {
  const dataStr = entry.data ? ` ${JSON.stringify(entry.data)}` : "";
  return `[${entry.timestamp}] [${entry.level.toUpperCase()}] [${entry.subsystem}] ${entry.message}${dataStr}`;
}

function writeEntry(entry: LogEntry): void {
  const minLevel = getMinLevel();
  if (logLevelPriority[entry.level] < logLevelPriority[minLevel]) return;

  const formatted = formatEntry(entry);

  switch (entry.level) {
    case "error":
      console.error(formatted);
      break;
    case "warn":
      console.warn(formatted);
      break;
    default:
      console.log(formatted);
  }
}

export function get_logger(subsystem: string) {
  return {
    debug(message: string, data?: Record<string, unknown>): void {
      writeEntry({ timestamp: new Date().toISOString(), level: "debug", subsystem, message, data });
    },
    info(message: string, data?: Record<string, unknown>): void {
      writeEntry({ timestamp: new Date().toISOString(), level: "info", subsystem, message, data });
    },
    warn(message: string, data?: Record<string, unknown>): void {
      writeEntry({ timestamp: new Date().toISOString(), level: "warn", subsystem, message, data });
    },
    error(message: string, data?: Record<string, unknown>): void {
      writeEntry({ timestamp: new Date().toISOString(), level: "error", subsystem, message, data });
    },
  };
}

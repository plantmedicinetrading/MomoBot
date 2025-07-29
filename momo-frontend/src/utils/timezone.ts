/**
 * Timezone utilities for consistent Eastern Time handling in the frontend.
 * All trade-related times should be displayed in Eastern Time.
 */

/**
 * Convert any date/time to Eastern Time for display
 */
export function toEasternTime(date: Date | string | number): Date {
  if (typeof date === 'string') {
    // Handle both Eastern Time timestamps (without timezone) and timezone-aware timestamps
    if (date.includes('T') && !date.includes('+') && !date.includes('-04:00') && !date.includes('-05:00')) {
      // This is an Eastern Time timestamp without timezone info (old format)
      // Parse as Eastern Time directly - don't add offset since it's already ET
      return new Date(date);
    } else {
      // This is already a timezone-aware timestamp (new format)
      date = new Date(date);
    }
  } else if (typeof date === 'number') {
    date = new Date(date * 1000); // Convert Unix timestamp to milliseconds
  }

  // Convert to Eastern Time
  return new Date(date.toLocaleString('en-US', { timeZone: 'America/New_York' }));
}

/**
 * Format date/time for display in Eastern Time
 */
export function formatEasternTime(date: Date | string | number, options?: Intl.DateTimeFormatOptions): string {
  const easternDate = toEasternTime(date);
  
  const defaultOptions: Intl.DateTimeFormatOptions = {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
    hour12: true,
    timeZone: 'America/New_York'
  };
  
  return easternDate.toLocaleString('en-US', options || defaultOptions);
}

/**
 * Convert Unix timestamp to Eastern Time string
 */
export function unixToEasternTime(unixTimestamp: number): string {
  return formatEasternTime(unixTimestamp * 1000);
}

/**
 * Get current time in Eastern Time
 */
export function getCurrentEasternTime(): Date {
  return new Date(new Date().toLocaleString('en-US', { timeZone: 'America/New_York' }));
}

/**
 * Convert Eastern Time string back to Unix timestamp
 */
export function easternTimeToUnix(easternTimeString: string): number {
  const date = new Date(easternTimeString);
  return Math.floor(date.getTime() / 1000);
}

/**
 * Format date for chart tooltip in Eastern Time
 * Note: Unix timestamps are always in UTC, so we convert to Eastern Time for display
 */
export function formatChartTime(unixTimestamp: number): { dateStr: string; timeStr: string } {
  const date = new Date(unixTimestamp * 1000);
  
  const timeStr = date.toLocaleTimeString('en-US', {
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
    hour12: false,
    timeZone: 'America/New_York'
  });
  
  const dateStr = date.toLocaleDateString('en-US', {
    month: 'short',
    day: 'numeric',
    year: 'numeric',
    timeZone: 'America/New_York'
  });
  
  return { dateStr, timeStr };
} 
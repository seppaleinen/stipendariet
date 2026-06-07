/**
 * Format foundation text by:
 * - Normalizing line breaks (\r\n -> \n)
 * - Unescaping slashes (\/ -> /)
 * - Unescaping quotes (\" -> ")
 * - Splitting into paragraphs on double newlines
 */
export function formatFoundationText(text: string | null | undefined): string[] {
  if (!text) return [];

  // Normalize Windows line breaks to Unix
  let formatted = text.replace(/\r\n/g, "\n");

  // Unescape forward slashes
  formatted = formatted.replace(/\\\//g, "/");

  // Unescape quotes
  formatted = formatted.replace(/\\"/g, '"');

  // Split on double newlines to get paragraphs
  const paragraphs = formatted.split(/\n\n+/).filter(p => p.trim());

  return paragraphs;
}

/**
 * Format a single paragraph, preserving single line breaks
 */
export function formatParagraph(text: string): string[] {
  // Split on single newlines
  return text.split(/\n/).filter(line => line.trim());
}

/**
 * Clean text for preview (cards, summaries) - simple cleanup without splitting
 */
export function cleanTextForPreview(text: string | null | undefined): string {
  if (!text) return "";

  return text
    .replace(/\r\n/g, " ")  // Replace Windows newlines with space
    .replace(/\n\n+/g, " ") // Replace double newlines with space
    .replace(/\n/g, " ")    // Replace single newlines with space
    .replace(/\\\//g, "/")  // Unescape slashes
    .replace(/\\"/g, '"')   // Unescape quotes
    .replace(/\s+/g, " ")   // Collapse multiple spaces
    .trim();
}

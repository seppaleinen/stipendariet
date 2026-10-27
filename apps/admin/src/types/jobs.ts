export type ActionState = {
  loading: boolean;
  message?: string;
  error?: string;
};

export type JobProgressState = {
  loading: boolean;
  message?: string;
  error?: string;
  progress?: number;
  completed?: number;
  total?: number;
  estimatedSecondsRemaining?: number | null;
};
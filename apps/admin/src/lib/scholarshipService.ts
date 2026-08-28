import { api, request } from '@/lib/api';
import { Scholarship, ScholarshipQueueItem } from '@/types';

const scholarshipService = {
  // Get scholarship queue (NEW and FAILED status)
  getQueue: async (): Promise<ScholarshipQueueItem[]> => {
    try {
      const response = await request(api.get('/scholarships/queue'));
      return response.data;
    } catch (error) {
      console.error('Error fetching scholarship queue:', error);
      throw error;
    }
  },

  // Trigger scraping for a specific scholarship
  triggerScrape: async (id: string): Promise<{ message: string }> => {
    try {
      const response = await request(api.post(`/scholarships/${id}/trigger-scrape`));
      return response.data;
    } catch (error) {
      console.error('Error triggering scrape:', error);
      throw error;
    }
  },

  // Get scholarship for review
  getForReview: async (id: string): Promise<Scholarship> => {
    try {
      const response = await request(api.get(`/scholarships/${id}/review`));
      return response.data;
    } catch (error) {
      console.error('Error fetching scholarship for review:', error);
      throw error;
    }
  },

  // Approve a scholarship
  approve: async (id: string): Promise<{ message: string; id: string; status: string }> => {
    try {
      const response = await request(api.patch(`/scholarships/${id}/approve`));
      return response.data;
    } catch (error) {
      console.error('Error approving scholarship:', error);
      throw error;
    }
  },
};

export default scholarshipService;
import React, { useState, useEffect } from 'react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { 
  Table, 
  TableBody, 
  TableCell, 
  TableHead, 
  TableHeader, 
  TableRow 
} from '@/components/ui/table';
import { Skeleton } from '@/components/ui/skeleton';
import { Play, Search, Eye } from 'lucide-react';
import { ScholarshipQueueItem } from '@/types';
import scholarshipService from '@/lib/scholarshipService';
import { useNavigate } from 'react-router-dom';

const QueuePage: React.FC = () => {
  const [queue, setQueue] = useState<ScholarshipQueueItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState('');
  const navigate = useNavigate();

  useEffect(() => {
    fetchQueue();
  }, []);

  const fetchQueue = async () => {
    try {
      setLoading(true);
      const data = await scholarshipService.getQueue();
      setQueue(data);
    } catch (error) {
      console.error('Error fetching queue:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleTriggerScrape = async (id: string) => {
    try {
      await scholarshipService.triggerScrape(id);
      // Refresh the queue after triggering scrape
      fetchQueue();
    } catch (error) {
      console.error('Error triggering scrape:', error);
    }
  };

  const filteredQueue = queue.filter(item => 
    item.name.toLowerCase().includes(searchTerm.toLowerCase()) || 
    item.organization_name.toLowerCase().includes(searchTerm.toLowerCase())
  );

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold">Scholarship Queue</h1>
        <p className="text-muted-foreground">
          Review and process scholarship entries with NEW or FAILED status
        </p>
      </div>

      <div className="flex flex-col sm:flex-row gap-4">
        <div className="relative flex-1">
          <Search className="absolute left-2 top-3 h-4 w-4 text-muted-foreground" />
          <input
            type="text"
            placeholder="Search scholarships..."
            className="pl-8 w-full p-2 border rounded-md"
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
          />
        </div>
        <Button onClick={fetchQueue}>
          Refresh Queue
        </Button>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Pending Items</CardTitle>
          <CardDescription>
            {queue.length} item(s) in the queue waiting for review or reprocessing
          </CardDescription>
        </CardHeader>
        <CardContent>
          {loading ? (
            <div className="space-y-4">
              {[...Array(5)].map((_, index) => (
                <div key={index} className="flex items-center space-x-4">
                  <Skeleton className="h-12 w-12 rounded-full" />
                  <div className="space-y-2 flex-1">
                    <Skeleton className="h-4 w-3/4" />
                    <Skeleton className="h-4 w-1/2" />
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Name</TableHead>
                  <TableHead>Organization</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead>Date Added</TableHead>
                  <TableHead className="text-right">Actions</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {filteredQueue.length > 0 ? (
                  filteredQueue.map((item) => (
                    <TableRow key={item.id}>
                      <TableCell className="font-medium">{item.name}</TableCell>
                      <TableCell>{item.organization_name}</TableCell>
                      <TableCell>
                        <Badge variant={item.status === 'NEW' ? 'default' : 'destructive'}>
                          {item.status}
                        </Badge>
                      </TableCell>
                      <TableCell>
                        {new Date(item.created_at).toLocaleDateString()}
                      </TableCell>
                      <TableCell className="text-right">
                        <div className="flex justify-end gap-2">
                          <Button
                            size="sm"
                            variant="outline"
                            onClick={() => navigate(`/review/${item.id}`)}
                          >
                            <Eye className="h-4 w-4 mr-2" />
                            Review
                          </Button>
                          <Button
                            size="sm"
                            onClick={() => handleTriggerScrape(item.id)}
                          >
                            <Play className="h-4 w-4 mr-2" />
                            Trigger Scrape
                          </Button>
                        </div>
                      </TableCell>
                    </TableRow>
                  ))
                ) : (
                  <TableRow>
                    <TableCell colSpan={5} className="text-center text-muted-foreground">
                      No items in the queue
                    </TableCell>
                  </TableRow>
                )}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>
    </div>
  );
};

export default QueuePage;
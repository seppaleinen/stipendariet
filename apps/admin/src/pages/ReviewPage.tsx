import React, { useState, useEffect } from 'react';
import { useParams } from 'react-router-dom';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Separator } from '@/components/ui/separator';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Skeleton } from '@/components/ui/skeleton';
import { AlertCircle, CheckCircle, FileText, ExternalLink } from 'lucide-react';
import { Scholarship } from '@/types';
import scholarshipService from '@/lib/scholarshipService';

const ReviewPage: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const [scholarship, setScholarship] = useState<Scholarship | null>(null);
  const [loading, setLoading] = useState(true);
  const [approving, setApproving] = useState(false);

  useEffect(() => {
    if (id) {
      fetchScholarship();
    }
  }, [id]);

  const fetchScholarship = async () => {
    try {
      setLoading(true);
      if (id) {
        const data = await scholarshipService.getForReview(id);
        setScholarship(data);
      }
    } catch (error) {
      console.error('Error fetching scholarship:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleApprove = async () => {
    if (!id) return;
    
    try {
      setApproving(true);
      await scholarshipService.approve(id);
      // In a real app, you might want to redirect or show a success message
      alert('Scholarship approved successfully!');
    } catch (error) {
      console.error('Error approving scholarship:', error);
      alert('Failed to approve scholarship');
    } finally {
      setApproving(false);
    }
  };

  if (loading) {
    return (
      <div className="space-y-6">
        <div>
          <Skeleton className="h-8 w-1/3" />
          <Skeleton className="h-4 w-1/4 mt-2" />
        </div>
        <Card>
          <CardHeader>
            <Skeleton className="h-6 w-1/2" />
          </CardHeader>
          <CardContent>
            <Skeleton className="h-4 w-full" />
            <Skeleton className="h-4 w-5/6 mt-2" />
            <Skeleton className="h-4 w-4/6 mt-2" />
          </CardContent>
        </Card>
      </div>
    );
  }

  if (!scholarship) {
    return (
      <div className="flex flex-col items-center justify-center py-12">
        <AlertCircle className="h-12 w-12 text-muted-foreground mb-4" />
        <h2 className="text-xl font-semibold mb-2">Scholarship Not Found</h2>
        <p className="text-muted-foreground mb-4">The scholarship you're looking for doesn't exist or has been removed.</p>
        <Button onClick={() => window.history.back()}>Go Back</Button>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div>
        <div className="flex items-center gap-2">
          <h1 className="text-3xl font-bold">Review Scholarship</h1>
          <Badge variant={scholarship.status === 'NEEDS_REVIEW' ? 'default' : 'secondary'}>
            {scholarship.status}
          </Badge>
        </div>
        <p className="text-muted-foreground">
          Compare AI-extracted data with raw scraped content and approve if accurate
        </p>
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <FileText className="h-5 w-5" />
              Extracted Data
            </CardTitle>
            <CardDescription>Information extracted by the AI from the source</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div>
              <h3 className="text-sm font-medium text-muted-foreground">Name</h3>
              <p className="text-lg">{scholarship.name || 'N/A'}</p>
            </div>
            
            <div>
              <h3 className="text-sm font-medium text-muted-foreground">Organization</h3>
              <p>{scholarship.organization_name || 'N/A'}</p>
            </div>
            
            {scholarship.description && (
              <div>
                <h3 className="text-sm font-medium text-muted-foreground">Description</h3>
                <p>{scholarship.description}</p>
              </div>
            )}
            
            {scholarship.requirements && (
              <div>
                <h3 className="text-sm font-medium text-muted-foreground">Requirements</h3>
                <p>{scholarship.requirements}</p>
              </div>
            )}
            
            {scholarship.amount && (
              <div>
                <h3 className="text-sm font-medium text-muted-foreground">Amount</h3>
                <p>{scholarship.amount}</p>
              </div>
            )}
            
            {scholarship.deadline && (
              <div>
                <h3 className="text-sm font-medium text-muted-foreground">Deadline</h3>
                <p>{scholarship.deadline}</p>
              </div>
            )}
            
            {scholarship.application_method && (
              <div>
                <h3 className="text-sm font-medium text-muted-foreground">Application Method</h3>
                <p>{scholarship.application_method}</p>
              </div>
            )}
            
            {scholarship.official_url && (
              <div>
                <h3 className="text-sm font-medium text-muted-foreground">Official URL</h3>
                <a 
                  href={scholarship.official_url} 
                  target="_blank" 
                  rel="noopener noreferrer"
                  className="flex items-center text-blue-500 hover:underline"
                >
                  {scholarship.official_url}
                  <ExternalLink className="h-4 w-4 ml-1" />
                </a>
              </div>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Raw Scraped Content</CardTitle>
            <CardDescription>Original content extracted from the scholarship website</CardDescription>
          </CardHeader>
          <CardContent>
            <ScrollArea className="h-[500px] rounded-md border p-4">
              <pre className="text-sm whitespace-pre-wrap">
                {scholarship.raw_scraped_content || 'No raw content available'}
              </pre>
            </ScrollArea>
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Review Actions</CardTitle>
          <CardDescription>Approve or reject this scholarship entry</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="flex gap-4">
            <Button 
              size="lg"
              className="flex-1"
              onClick={handleApprove}
              disabled={approving}
            >
              {approving ? (
                'Approving...'
              ) : (
                <>
                  <CheckCircle className="h-5 w-5 mr-2" />
                  Approve & Publish
                </>
              )}
            </Button>
            <Button 
              size="lg" 
              variant="outline" 
              className="flex-1"
              onClick={() => window.history.back()}
            >
              Cancel
            </Button>
          </div>
          <Separator className="my-4" />
          <p className="text-sm text-muted-foreground">
            By approving this entry, it will be made publicly available and vector embeddings will be generated for search functionality.
          </p>
        </CardContent>
      </Card>
    </div>
  );
};

export default ReviewPage;
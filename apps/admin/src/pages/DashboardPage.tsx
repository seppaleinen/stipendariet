import React from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '@/hooks/useAuth';

const DashboardPage: React.FC = () => {
  const navigate = useNavigate();
  const { user, logout } = useAuth();

  const handleLogout = () => {
    logout();
    navigate('/login');
  };

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-3xl font-bold">Admin Dashboard</h1>
          <p className="text-muted-foreground">Manage scholarships and review pending applications</p>
        </div>
        <Button onClick={handleLogout} variant="outline">
          Logout
        </Button>
      </div>

      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
        <Card>
          <CardHeader>
            <CardTitle>Scholarship Queue</CardTitle>
            <CardDescription>Items pending review</CardDescription>
          </CardHeader>
          <CardContent>
            <Button 
              onClick={() => navigate('/queue')} 
              className="w-full"
            >
              View Queue
            </Button>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Review Processed Items</CardTitle>
            <CardDescription>Recently processed scholarship data</CardDescription>
          </CardHeader>
          <CardContent>
            <p className="text-sm text-muted-foreground">Coming soon</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Statistics</CardTitle>
            <CardDescription>Overall platform metrics</CardDescription>
          </CardHeader>
          <CardContent>
            <p className="text-sm text-muted-foreground">Coming soon</p>
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Welcome, {user?.name}</CardTitle>
          <CardDescription>
            You have administrative access to manage scholarship data. Use the navigation to review and approve entries.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <p className="text-sm">
            The Data Engine continuously discovers and processes new scholarship information. 
            Your role is to review and approve these entries before they are made public.
          </p>
        </CardContent>
      </Card>
    </div>
  );
};

export default DashboardPage;
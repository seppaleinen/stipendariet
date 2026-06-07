import React, { useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { backendApi } from '@/lib/api';
import { ActionState } from '@/types/jobs';

export const SystemActionsCard: React.FC = () => {
  const [state, setState] = useState<Record<string, ActionState>>({});

  const triggerAction = async (key: string, endpoint: string, confirmText?: string) => {
    if (confirmText && !window.confirm(confirmText)) return;

    setState((prev) => ({ ...prev, [key]: { loading: true } }));
    try {
      const response = await backendApi.post(endpoint);
      setState((prev) => ({ 
        ...prev, 
        [key]: { loading: false, message: JSON.stringify(response.data, null, 2) } 
      }));
    } catch (e: any) {
      setState((prev) => ({ 
        ...prev, 
        [key]: { loading: false, error: e.message } 
      }));
    }
  };

  return (
    <div className="space-y-4">
      <Card>
        <CardHeader><CardTitle>Kategorisering</CardTitle></CardHeader>
        <CardContent className="space-y-3">
          <p className="text-sm text-muted-foreground">Återställ och kör om kategorisering.</p>
          <div className="flex gap-2">
            <Button onClick={() => triggerAction('reset', '/admin/reset-categories')}>Återställ</Button>
            <Button onClick={() => triggerAction('trigger', '/admin/trigger-bulk-categorization')}>Kör Bulk</Button>
          </div>
          {state.reset?.message && <p className="text-sm text-green-600">Reset klar</p>}
          {state.trigger?.message && <p className="text-sm text-green-600">Startad!</p>}
        </CardContent>
      </Card>

      <Card className="border-destructive/50">
        <CardHeader><CardTitle className="text-destructive">Farliga Åtgärder</CardTitle></CardHeader>
        <CardContent className="space-y-3">
          <Button 
            variant="destructive" 
            onClick={() => triggerAction('clear', '/admin/clear-database', 'ÄR DU SÄKER? Detta rensar ALLT.')}
          >
            Rensa Databas
          </Button>
          {state.clear?.message && <p className="text-sm text-destructive">Databas rensad</p>}
        </CardContent>
      </Card>
    </div>
  );
};

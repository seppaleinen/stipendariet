import { Bookmark } from "lucide-react";
import { Button } from "@stipendariet/ui";
import { Badge } from "@stipendariet/ui";
import {
  Card,
  CardContent,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle,
} from "@stipendariet/ui";
import { Link } from "react-router-dom";
import type { Grant } from "../types";

interface GrantCardProps {
  grant: Grant;
  isSaved: boolean;
  isSaving: boolean;
  onSaveToggle: (grantId: string, shouldSave: boolean) => void;
}

export function GrantCard({
  grant,
  isSaved,
  isSaving,
  onSaveToggle,
}: GrantCardProps) {
  return (
    <Card className="flex flex-col hover:shadow-lg transition-shadow">
      <CardHeader>
        <div className="flex items-start justify-between mb-2">
          <Badge variant="secondary">{grant.category}</Badge>
          <div className="flex gap-2">
            <Button
              variant="ghost"
              size="icon"
              className="h-8 w-8"
              disabled={isSaving}
              onClick={() => onSaveToggle(grant.id, !isSaved)}
              aria-label={isSaved ? `Ta bort ${grant.title} från sparade` : `Spara ${grant.title}`}
            >
              {isSaved ? (
                <Bookmark className="h-4 w-4 fill-current" aria-hidden="true" />
              ) : (
                <Bookmark className="h-4 w-4" aria-hidden="true" />
              )}
            </Button>
          </div>
        </div>
        <CardTitle className="line-clamp-2">{grant.title}</CardTitle>
        <CardDescription className="line-clamp-3">
          {grant.summary}
        </CardDescription>
      </CardHeader>

      <CardContent className="flex-1">
        <div className="space-y-2 text-sm">
          <div className="flex justify-between">
            <span className="text-muted-foreground">Utgivare:</span>
            <span className="font-medium">{grant.provider}</span>
          </div>
          {grant.amount && (
            <div className="flex justify-between">
              <span className="text-muted-foreground">Belopp:</span>
              <span className="font-medium">{grant.amount}</span>
            </div>
          )}
          {grant.deadline && (
            <div className="flex justify-between">
              <span className="text-muted-foreground">Deadline:</span>
              <span className="font-medium">{grant.deadline}</span>
            </div>
          )}
        </div>

        <div className="flex flex-wrap gap-2 mt-4">
          {grant.tags.slice(0, 3).map((tag) => (
            <Badge key={tag} variant="outline" className="text-xs">
              {tag}
            </Badge>
          ))}
        </div>
      </CardContent>

      <CardFooter>
        <Button asChild className="w-full">
          <Link to={`/grants/${grant.id}`}>Läs mer</Link>
        </Button>
      </CardFooter>
    </Card>
  );
}
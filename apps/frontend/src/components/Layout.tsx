import { Link, useLocation } from "react-router-dom";
import { Home, Search, FileText, PenSquare, Users, LogIn, LogOut, Loader2 } from "lucide-react";
import { cn } from "@/lib/utils";
import { useAuth } from "@/contexts/AuthContext";
import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
import { ProfileSwitcher } from "@/components/ProfileSwitcher";

export default function Layout({ children }: { children: React.ReactNode }) {
  const location = useLocation();
  const { user, isAuthenticated, isLoading, logout } = useAuth();

  // Public navigation items (always visible)
  const publicNavigation = [
    { name: "Hem", href: "/", icon: Home },
    { name: "Stipendier", href: "/grants", icon: Search },
  ];

  // Protected navigation items (only when logged in)
  const protectedNavigation = [
    { name: "Familj", href: "/family-setup", icon: Users },
    { name: "Ansökningar", href: "/applications", icon: FileText },
    { name: "Skapa Ansökan", href: "/generate", icon: PenSquare },
  ];

  const navigation = isAuthenticated
    ? [...publicNavigation, ...protectedNavigation]
    : publicNavigation;

  const handleLogout = async () => {
    await logout();
  };

  const getInitials = (name?: string, email?: string) => {
    if (name) {
      return name.split(" ").map(n => n[0]).join("").toUpperCase().slice(0, 2);
    }
    if (email) {
      return email[0].toUpperCase();
    }
    return "U";
  };

  return (
    <div className="min-h-screen bg-background">
      {/* Skip link for keyboard navigation */}
      <a href="#main-content" className="skip-link">
        Hoppa till huvudinnehåll
      </a>

      <header className="sticky top-0 z-50 w-full border-b bg-card/95 backdrop-blur supports-[backdrop-filter]:bg-card/60">
        <div className="container flex h-16 items-center justify-between">
          <Link to="/" className="flex items-center space-x-2" aria-label="StipendieAssistenten - Gå till startsidan">
            <div className="h-8 w-8 rounded-lg bg-primary flex items-center justify-center" aria-hidden="true">
              <span className="text-primary-foreground font-bold text-xl">
                S
              </span>
            </div>
            <span className="font-bold text-xl">StipendieAssistenten</span>
          </Link>

          <div className="flex items-center gap-4">
            <nav className="hidden md:flex gap-6" aria-label="Huvudnavigering">
              {navigation.map((item) => {
                const Icon = item.icon;
                const isActive = location.pathname === item.href;
                return (
                  <Link
                    key={item.name}
                    to={item.href}
                    aria-current={isActive ? "page" : undefined}
                    className={cn(
                      "flex items-center gap-2 text-sm font-medium transition-colors hover:text-primary",
                      isActive ? "text-primary" : "text-muted-foreground",
                    )}
                  >
                    <Icon className="h-4 w-4" aria-hidden="true" />
                    {item.name}
                  </Link>
                );
              })}
            </nav>

            {/* Auth section */}
            {isLoading ? (
              <>
                <Loader2 className="h-5 w-5 animate-spin text-muted-foreground" aria-hidden="true" />
                <span className="sr-only">Laddar användarinformation...</span>
              </>
            ) : isAuthenticated ? (
              <div className="flex items-center gap-4">
                <ProfileSwitcher />
                <DropdownMenu>
                  <DropdownMenuTrigger asChild>
                    <Button variant="ghost" className="relative h-9 w-9 rounded-full">
                    <Avatar className="h-9 w-9">
                      <AvatarImage src={user?.avatar} alt={user?.name || user?.email} />
                      <AvatarFallback className="bg-primary text-primary-foreground">
                        {getInitials(user?.name, user?.email)}
                      </AvatarFallback>
                    </Avatar>
                  </Button>
                </DropdownMenuTrigger>
                <DropdownMenuContent align="end" className="w-56">
                  <div className="flex items-center gap-2 p-2">
                    <div className="flex flex-col space-y-1 leading-none">
                      {user?.name && (
                        <p className="font-medium">{user.name}</p>
                      )}
                      <p className="text-sm text-muted-foreground truncate">
                        {user?.email}
                      </p>
                    </div>
                  </div>
                  <DropdownMenuSeparator />
                  <DropdownMenuItem asChild>
                    <Link to="/family-setup" className="cursor-pointer">
                      <Users className="mr-2 h-4 w-4" />
                      Min profil
                    </Link>
                  </DropdownMenuItem>
                  <DropdownMenuItem asChild>
                    <Link to="/applications" className="cursor-pointer">
                      <FileText className="mr-2 h-4 w-4" />
                      Mina ansökningar
                    </Link>
                  </DropdownMenuItem>
                  <DropdownMenuSeparator />
                  <DropdownMenuItem onClick={handleLogout} className="cursor-pointer text-destructive focus:text-destructive">
                    <LogOut className="mr-2 h-4 w-4" />
                    Logga ut
                  </DropdownMenuItem>
                </DropdownMenuContent>
                </DropdownMenu>
              </div>
            ) : (
              <Button asChild variant="default" size="sm">
                <Link to="/auth">
                  <LogIn className="mr-2 h-4 w-4" />
                  Logga in
                </Link>
              </Button>
            )}
          </div>
        </div>
      </header>

      <main id="main-content" className="container py-8 pb-24 md:pb-8">{children}</main>

      {/* Mobile Navigation */}
      <nav className="md:hidden fixed bottom-0 left-0 right-0 border-t bg-card" aria-label="Mobilnavigering">
        <div className={cn(
          "grid gap-1 p-2",
          isAuthenticated ? "grid-cols-5" : "grid-cols-3"
        )}>
          {navigation.map((item) => {
            const Icon = item.icon;
            const isActive = location.pathname === item.href;
            return (
              <Link
                key={item.name}
                to={item.href}
                aria-current={isActive ? "page" : undefined}
                className={cn(
                  "flex flex-col items-center justify-center py-2 rounded-lg transition-colors",
                  isActive
                    ? "text-primary bg-primary/10"
                    : "text-muted-foreground hover:text-primary",
                )}
              >
                <Icon className="h-5 w-5" aria-hidden="true" />
                <span className="text-xs mt-1">{item.name}</span>
              </Link>
            );
          })}
          {!isAuthenticated && (
            <Link
              to="/auth"
              className={cn(
                "flex flex-col items-center justify-center py-2 rounded-lg transition-colors",
                location.pathname === "/auth"
                  ? "text-primary bg-primary/10"
                  : "text-muted-foreground hover:text-primary",
              )}
            >
              <LogIn className="h-5 w-5" />
              <span className="text-xs mt-1">Logga in</span>
            </Link>
          )}
        </div>
      </nav>
    </div>
  );
}

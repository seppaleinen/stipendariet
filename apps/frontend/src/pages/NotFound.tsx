import { Helmet } from "react-helmet-async";
import { useLocation, Link } from "react-router-dom";
import { useEffect } from "react";

const NotFound = () => {
  const location = useLocation();

  useEffect(() => {
    console.error(
      "404 Error: User attempted to access non-existent route:",
      location.pathname,
    );
  }, [location.pathname]);

  return (
    <>
      <Helmet>
        <title>404 - Sida hittades inte | StipendieAssistenten</title>
        <meta name="description" content="Sidan du letar efter finns inte." />
        <meta name="robots" content="noindex, nofollow" />
      </Helmet>
      <div className="flex min-h-screen items-center justify-center bg-muted">
        <div className="text-center">
          <h1 className="mb-4 text-4xl font-bold">404</h1>
          <p className="mb-4 text-xl text-muted-foreground">
            Sidan hittades inte
          </p>
          <Link to="/" className="text-primary underline hover:text-primary/90">
            Till startsidan
          </Link>
        </div>
      </div>
    </>
  );
};

export default NotFound;

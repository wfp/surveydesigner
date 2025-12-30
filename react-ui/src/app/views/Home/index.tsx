import React, { useEffect } from "react";
import { Navigate } from "react-router-dom";
import { useAppSelector } from "../../redux/store";

import LandingPage from "../../components/LandingPage";

function Home() {
  const auth = useAppSelector((state) => state.auth);
  const isAuth = auth.is_logged;

  const storedLocation = localStorage.getItem("from");
  const from = storedLocation ? JSON.parse(storedLocation) : undefined;
  const redirectTo = from?.pathname || "/design/survey";

  useEffect(() => {
    if (isAuth && from) {
      localStorage.removeItem("from");
    }
  }, [from, isAuth]);
  return isAuth ? <Navigate to={redirectTo} replace /> : <LandingPage />;
}

export default Home;

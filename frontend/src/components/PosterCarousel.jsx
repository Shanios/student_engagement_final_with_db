import { useState, useEffect } from "react";

import poster1 from "../assets/posters/poster1.png";
import poster2 from "../assets/posters/poster2.png";


// Add / remove posters as you like
const POSTERS = [
  { id: 1, src: poster1, alt: "Exam timetable" },
  { id: 2, src: poster2, alt: "New syllabus update" },
  
];

export default function PosterCarousel() {
  const [index, setIndex] = useState(0);

  // Auto-slide every 5 seconds
  useEffect(() => {
    if (POSTERS.length <= 1) return;

    const id = setInterval(() => {
      setIndex((prev) => (prev + 1) % POSTERS.length);
    }, 5000); // 5 seconds

    return () => clearInterval(id);
  }, []);

  return (
    <div className="poster-carousel">
      <div
        className="poster-track"
        style={{ transform: `translateX(-${index * 100}%)` }}
      >
        {POSTERS.map((p) => (
          <div className="poster-slide" key={p.id}>
            <img src={p.src} alt={p.alt} />
          </div>
        ))}
      </div>
    </div>
  );
}

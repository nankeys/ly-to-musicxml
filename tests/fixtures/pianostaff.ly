\version "2.26.0"

\score {
  \new PianoStaff <<
    \new Staff = "right" {
      \clef treble
      c''4 ( d'' e'' f'' )
    }
    \new Staff = "left" {
      \clef bass
      c4 ( d e f )
    }
  >>
}

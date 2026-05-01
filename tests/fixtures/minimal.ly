\version "2.26.0"

\score {
  \new Staff \relative c' {
    \tempo "Andante" 4 = 80
    \time 4/4
    \key c \minor
    c4\p d ees f |
    g1 \bar "|."
  }
}
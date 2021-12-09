program ReadDiag
  use ReadDiagMod
  implicit none
  integer, parameter :: StrLen = 512
  character(len=StrLen) :: FileName
  integer :: ios
  integer :: ipe
  integer :: lu
  integer :: i, k
  integer :: iret

!  integer, parameter :: nlev = 14
!  real, parameter, dimension(nlev) :: levs = (/       &
!       1000.0,&
!       900.0,&
!       800.0,&
!       700.0,&
!       600.0,&
!       500.0,&
!       400.0,&
!       300.0,&
!       250.0,&
!       200.0,&
!       150.0,&
!       100.0,&
!       50.0,&
!       0.0  &
!       /)
  integer, parameter  :: i_kind   = selected_int_kind(8)
  integer, parameter  :: r_single = selected_real_kind(6)

  type(diag)    :: DiagConv


  iret = DiagConv%Open('teste')
  iret = DiagConv%CalcStat()
  iret = DiagConv%PrintCount()
  print*,'    t'
  
  Print*, DiagConv%GetTotalObs()

  Print*, DiagConv%GetNObs('      t        ')

  Print*, DiagConv%GetNObs('     ps         ')
  Print*, DiagConv%GetNObs(' uv ')
  Print*, DiagConv%GetNObs('sst')

  stop 'Done. Ends Normally'

997 STOP 'error read in diag file 997'
999 STOP 'error read in diag file 999'

end program ReadDiag

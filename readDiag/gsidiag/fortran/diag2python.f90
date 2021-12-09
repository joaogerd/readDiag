module Diag2Python
   use ReadDiagMod
   Implicit None
   Private

   Public :: open
   Public :: close
   Public :: GetObs
   Public :: GetVarNames
   Public :: GetVarInfo
   Public :: GetnVars
!   Public :: Gobt


   Real, Public, Allocatable :: Array1D(    :)
   Real, Public, Allocatable :: Array2D(  :,:)
   Real, Public, Allocatable :: Array3D(:,:,:)

   Character(len=32), Public, Allocatable :: CharArray1D(  :)
   Character(len=32), Public, Allocatable :: CharArray2D(:,:)

   type acc
      integer            :: FNumber
      character(len=512) :: FileName
      character(len=512) :: FileName2
      integer            :: iret
      type(diag)         :: conv
      type(acc), pointer :: next => null()
   end type

   Type(acc),  pointer :: d     => null()
   type(acc),  pointer :: dRoot => null()
   type(acc),  pointer :: tmp   => null()
   Type(node), pointer :: ObsRoot => null()

   integer :: FileCount
   
   contains

   function open(FileName, FileName2) result(FNumber)
      Character(len=*), intent(in) :: FileName
      Character(len=*), intent(in) :: FileName2
      Integer                      :: FNumber

      character(len=512) :: N1, N2

      !
      ! First open file
      !

      if(.not.associated(dRoot))then


         allocate(dRoot)
         d => dRoot
         if(len_trim(FileName2).eq.0)then
            d%iret     = d%conv%open(trim(FileName))
         else
            d%iret     = d%conv%open(trim(FileName),trim(FileName2))
         endif

         if( d%iret .eq. 0 )then
            FileCount  = 1
            d%Fnumber  = FileCount
            d%FileName = trim(adjustl(FileName))
            FNumber    = d%FNumber
         else
            deallocate(dRoot)
            FNumber = -1
         endif
         

      else

         !
         ! Verify if file is already open
         !
         
         N1 = trim(adjustl(FileName))

         d => dRoot
         do while(associated(d))
            N2 = trim(adjustl(d%FileName))

            if(trim(N1).eq.trim(N2))then
               write(*,'(A,1x,A)')'File already open:',trim(N1)
               FNumber = d%FNumber
               return
            endif

            if(associated(d%next)) then
               d=>d%next
            else
               exit
            endif

         enddo

         !
         ! It's not open
         !
         allocate(d%next)
         tmp => d%next
         if(len_trim(FileName2).eq.0)then
            tmp%iret     = tmp%conv%open(trim(FileName))
         else
            tmp%iret     = tmp%conv%open(trim(FileName),trim(FileName2))
         endif

         if(tmp%iret .eq. 0 )then

            FileCount    = FileCount + 1
            tmp%FNumber  = FileCount
            tmp%FileName = trim(FileName)
            FNumber      = tmp%FNumber
            d => tmp

         else
            deallocate(d%next)
            FNumber = -1
            
         endif

      endif

   end function

   function close(FNumber) result(iret)
      Integer, intent(in) :: FNumber
      Integer             :: iret
      Type(acc), pointer  :: curr => null()
      Type(acc), pointer  :: prev => null()

      iret = 0

      prev => dRoot
      curr => dRoot%next

      if (prev%FNumber .eq. FNumber)then

         iret = prev%conv%close()
         
         deallocate(prev)
         dRoot => curr
         return

      endif

      do while(associated(curr))

         if(curr%FNumber .eq. FNumber) then
            
            prev%next => curr%next

            iret = curr%conv%close()

            deallocate(curr)

            exit
            
         endif

         prev => curr
         curr => curr%next
      enddo
   end function

!   subroutine GetVarNames(FNumber, nVars)
!      integer,          intent(in   ) :: FNumber
!      integer,          intent(  out) :: nVars
!
!      type(ObsInfo), pointer :: ObsNow => null()
!      integer :: i
!
!      !
!      ! Release array1d if allocated
!      !
!
!      if(allocated(CharArray1D)) deallocate(CharArray1D)
!
!      !
!      ! Find by file opened
!      !
!
!      d => dRoot
!      do while(associated(d))
!         if(FNumber.eq.d%FNumber) exit
!         d => d%next
!      enddo
!      
!      !
!      ! Get first variable
!      !
!
!      call d%conv%GetFirstVar(ObsNow)
!
!      !
!      ! Count VarNames ready to use
!      !
!      nVars = 0
!      do while(associated(ObsNow))
!         nVars = nVars + 1
!         ObsNow => ObsNow%NextVar
!      enddo
!
!      !
!      ! Get first variable again
!      !
!
!      call d%conv%GetFirstVar(ObsNow)
!
!      !
!      ! pickup VarNames ready to use
!      !
!      allocate(CharArray1D(nVars))
!      do i=1,nVars
!         CharArray1D(i) = trim(adjustl(ObsNow%VarName))
!         ObsNow => ObsNow%NextVar
!      enddo
!
!   end subroutine

   subroutine GetVarInfo(FNumber, VarName, nKx)
      integer,          intent(in   ) :: FNumber
      character(len=*), intent(in   ) :: VarName
      integer,          intent(  out) :: nKx

      type(ObsInfo), pointer :: ObsNow => null()
      type(ObsType), pointer :: oType => null()

      character(len=10) :: v1, v2

      integer :: i

      !
      ! Release array2d if allocated
      !

      if(allocated(Array2D)) deallocate(Array2D)

      !
      ! Find by file opened
      !

      d => dRoot
      do while(associated(d))
         if(FNumber.eq.d%FNumber) exit
         d => d%next
      enddo
      
      !
      ! Get first variable
      !

      call d%conv%GetFirstVar(ObsNow)

      !
      ! Find by VarName
      !
      v1 = trim(adjustl(VarName))
      do while(associated(ObsNow))

         v2 = trim(adjustl(ObsNow%VarName))

         !now find by ObsType (kx)
         if(v1 .eq. v2) then

           oType => ObsNow%OT%FirstKX
           nKx = ObsNow%nKx
           allocate(Array2D(ObsNow%nKx,2))
           do i=1,ObsNow%nKx
              Array2D(i,1) = oType%kx
              Array2D(i,2) = oType%nobs
              oType => oType%nextKX
           enddo
          
         endif

         ObsNow => ObsNow%NextVar
      enddo

   end subroutine

   function getnvars(FNumber) result(nVars)
      integer, intent(in   ) :: FNumber
      integer                :: nVars

      !
      ! Find by file opened
      !

      d => dRoot
      do while(associated(d))
         if(FNumber.eq.d%FNumber) exit
         d => d%next
      enddo

      !
      ! Get number of variables
      !

      nVars = d%conv%nVars

   end function

   subroutine GetVarNames(FNumber, nVars, VarNames)
      integer, intent(in) :: FNumber
      integer, intent(in) :: nVars
      character(len=3), dimension(nVars), intent(out) :: VarNames

      type(ObsInfo), pointer :: ObsRoot => null()
      type(ObsInfo), pointer :: tmpObs => null()

      integer :: i

      !
      ! Release array1d if allocated
      !

!      if(allocated(CharArray1D)) deallocate(CharArray1D)

      !
      ! Find by file opened
      !

      d => dRoot
      do while(associated(d))
         if(FNumber.eq.d%FNumber) exit
         d => d%next
      enddo

      !
      ! Get first variable
      !

      call d%conv%GetFirstVar(ObsRoot)

!      nVars = d%conv%nVars
!      allocate(CharArray1D(nVars))

      tmpObs => ObsRoot
      i = 1
      do i = 1, nVars !while(associated(tmpObs))

         !CharArray1D(i) = trim(tmpObs%VarName)
         VarNames(i) = trim(tmpObs%VarName)
!         i              = i + 1
         tmpObs         => tmpObs%NextVar
      enddo

   end subroutine

   subroutine GetObs  (FNumber, oName, oType, zlevs, n, NObs)
      integer,          intent(in   ) :: FNumber
      character(len=*), intent(in   ) :: oName
      integer,          intent(in   ) :: oType
      integer,          intent(in   ) :: n
      real,             intent(in   ) :: zlevs(n)
      integer,          intent(  out) :: NObs

      type(ObsInfo), pointer :: ObsNow => null()
      type(ObsType), pointer :: Now => null()
      Type(node),    pointer :: Obs => null()

      integer :: i, k
      character(len=512) :: N1, N2
      character(len=3) :: v1, v2

      !
      ! Release array2d if allocated
      !

      if(allocated(Array2D)) deallocate(Array2D)

      !
      ! Find File Number
      !

      d => dRoot
      do while(associated(d))
         if(FNumber.eq.d%FNumber) exit
         d => d%next
      enddo

      if(.not.associated(d)) then
         print*, 'No file open ... ', FNumber
         return
      endif

      Array2D = d%conv%GetObsInfo(oName, oType, zlevs)
      nObs    = size(Array2D,1)

!      !
!      ! Get first variable
!      !
!
!      call d%conv%GetFirstVar(ObsNow)
!
!      !
!      ! Find by VarName
!      !
!      v1 = trim(adjustl(oName))
!      FindVar : do while(associated(ObsNow))
!
!         v2 = trim(adjustl(ObsNow%VarName))
!
!         if(v1 .eq. v2) then
!
!           !now find by ObsType (kx)
!
!           Now => ObsNow%OT%FirstKX
!
!           do while(associated(Now))
!
!              if(int(Now%kx) .eq. oType)then
!                 nObs = Now%nObs
!
!                 select case (trim(v1))
!                    case('q')
!                       allocate(Array2D(Now%nobs,21))
!                    case('uv')
!                       allocate(Array2D(Now%nobs,21))
!                    case('t')
!                       allocate(Array2D(Now%nobs,22))
!                    case('sst')
!                       allocate(Array2D(Now%nobs,24))
!                    case default
!                       allocate(Array2D(Now%nobs,20))
!                 end select
!
!
!                 Obs => Now%head
!
!                 do i=1,Now%nObs
!                    k = minloc(Obs%data%prs-zlevs,mask=(Obs%data%prs-zlevs).ge.0,DIM=1)
!
!                    Array2D(i, 1) = Obs%data%lat     ! observation latitude (degrees)
!                    Array2D(i, 2) = Obs%data%lon     ! observation longitude (degrees)
!                    Array2D(i, 3) = Obs%data%elev    ! station elevation (meters)
!                    Array2D(i, 4) = Obs%data%prs     ! observation pressure (hPa)
!                    Array2D(i, 5) = Obs%data%dhgt    ! observation height (meters)
!                    Array2D(i, 6) = zlevs(k)         ! observation reference level (hPa)
!                    Array2D(i, 7) = Obs%data%time    ! obs time (minutes relative to analysis time)
!                    Array2D(i, 8) = Obs%data%pbqc    ! input prepbufr qc or event mark
!                    Array2D(i, 9) = Obs%data%iuse    ! analysis usage flag (1=use, -1=monitoring )
!                    Array2D(i,10) = Obs%data%iusev   ! analysis usage flag ( value )
!                    Array2D(i,11) = Obs%data%wpbqc   ! nonlinear qc relative weight
!                    Array2D(i,12) = Obs%data%inp_err ! prepbufr inverse obs error (unit**-1)
!                    Array2D(i,13) = Obs%data%adj_err ! read_prepbufr inverse obs error (unit**-1)
!                    Array2D(i,14) = Obs%data%end_err ! final inverse observation error (unit**-1)
!                    Array2D(i,15) = Obs%data%robs    ! observation
!                    Array2D(i,16) = Obs%data%omf     ! obs-ges used in analysis (K)
!                    Array2D(i,17) = Obs%data%oma     ! obs-anl used in analysis (K)
!                    Array2D(i,18) = Obs%data%imp     ! observation impact
!                    Array2D(i,19) = Obs%data%dfs     ! degree of freedom for signal
!                    Array2D(i,20) = Obs%data%kx
!
!                    select case(trim(v1))
!                       case('q')
!                          Array2D(i,21) = Obs%data%qsges ! guess saturation specific humidity
!                       case('uv')
!                          Array2D(i,21) = Obs%data%factw ! 10m wind reduction factor
!                       case('t')
!                          Array2D(i,21) = Obs%data%pof ! data pof
!                          Array2D(i,22) = Obs%data%wvv ! data vertical velocity
!                       case('sst')
!                          Array2D(i,21) = Obs%data%tref ! sst Tr (adiative transfer model)
!                          Array2D(i,22) = Obs%data%dtw  ! sst dt_warm at zob
!                          Array2D(i,23) = Obs%data%dtc  ! sst dt_cool at zob
!                          Array2D(i,24) = Obs%data%tz   ! sst d(tz)/d(tr) at zob
!                    end select
!
!                    Obs => Obs%next
!
!                 enddo
!
!              endif
!
!              Now => Now%next
!           enddo
!
!           exit FindVar
!
!         endif
!
!         ObsNow => ObsNow%NextVar
!         
!      enddo FindVar
   
   end subroutine

!   subroutine GetObs_(FNumber, ObsName, ObsType, NObs, zlevs)
!      integer,          intent(in   ) :: FNumber
!      character(len=*), intent(in   ) :: ObsName
!      integer,          intent(in   ) :: ObsType
!      real, optional,   intent(in   ) :: zlevs(:)
!      integer,          intent(  out) :: NObs
!
!      type(ObsInfo), pointer :: FullObs => null()
!      Type(node),    pointer :: Obs => null()
!      type(node),    pointer :: Now => null()
!
!      integer :: i, k
!      character(len=512) :: N1, N2
!      character(len=3) :: v1, v2
!      real, pointer :: levs(:) => null()
!
!      !
!      ! Find by file opened
!      !
!
!      d => dRoot
!      do while(associated(d))
!         if(FNumber.eq.d%FNumber) exit
!         d => d%next
!      enddo
!
!      call d%conv%GetFirstVar(FullObs)
!
!
!      v1 = trim(adjustl(ObsName))
!      NObs = 0
!      do while(associated(FullObs))
!         v2 = trim(adjustl(FullObs%VarName))
!
!         if(v1 .eq. v2) then
!
!           Now => FullObs%head
!           do while(associated(Now))
!
!              if(Now%data%kx .eq. ObsType)then
!
!                 if(.not.associated(ObsRoot))then
!                    allocate(ObsRoot)
!                    Obs => ObsRoot
!                 endif
!                 Obs%data = Now%data 
!
!                 allocate(Obs%next)
!                 Obs => Obs%next
!
!                 NObs = NObs + 1
!              endif
!
!              Now => Now%next
!           enddo
!          
!         endif
!
!         FullObs => FullObs%NextVar
!      enddo
!      if (nObs .eq. 0 ) return
!      
!      !------------------------------------------!
!      ! what are the standard atmospheric levels 
!      !
!      if(present(zlevs))then
!         allocate(levs(size(zlevs)))
!         levs = zlevs
!      else
!         levs => default_levs
!      endif
!      !
!      !------------------------------------------!
!
!
!      if(allocated(array2d)) deallocate(array2d)
!      allocate(array2d(nObs,12))
!      
!      Obs => ObsRoot
!      i=1
!      do while(i.le.NObs)
!         k = minloc(Obs%data%prs-levs,mask=(Obs%data%prs-levs).ge.0,DIM=1)
!
!         Array2d(i, 1)= Obs%data%lat   ! observation latitude (degrees)
!         Array2d(i, 2)= Obs%data%lon   ! observation longitude (degrees)
!         Array2d(i, 3)= Obs%data%prs   ! observation pressure (hPa)
!         Array2d(i, 4)= levs(k)        ! standard pressure level(hPa)
!         Array2d(i, 5)= Obs%data%time  ! obs time (minutes relative to analysis time)
!         Array2d(i, 6)= Obs%data%pbqc  ! input prepbufr qc or event mark
!         Array2d(i, 7)= Obs%data%iuse  ! analysis usage flag (1=use, -1=monitoring )
!         Array2d(i, 8)= Obs%data%iusev ! analysis usage flag ( value )
!         Array2d(i, 9)= Obs%data%robs  ! observation
!         Array2d(i,10)= Obs%data%diff  ! obs-ges used in analysis (K)
!         Array2d(i,11)= Obs%data%rmod
!         Array2d(i,12)= Obs%data%kx
!
!         Obs => Obs%next
!         i = i + 1
!      enddo
!      
!      !
!      ! clean up Obs and ObsRoot pointers
!      !
!
!      Obs => ObsRoot%next
!      do 
!         deallocate (ObsRoot)
!         if(.not.associated(Obs)) exit
!         ObsRoot => Obs
!         Obs => Obs%next
!      enddo
!
!   
!   end subroutine

end module

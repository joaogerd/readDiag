!-----------------------------------------------------------------------------!
!           Group on Data Assimilation Development - GDAD/CPTEC/INPE          !
!-----------------------------------------------------------------------------!
!BOI
!
! ! TITLE: GSI Diagnostic Tool Documentation \\ Version 1.0.0
!
! !AUTHORS: Jo\~a Gerd Z. de Mattos
!
! !AFFILIATION: Group on Data Assimilation Development, CPTEC/INPE, Cachoeira Paulista - SP
! 
! !DATE: May 15, 2012
!
! !INTRODUCTION: Package Overview
!
!    ReadDiagMod is a Fortran 90 collection of routines/functions for 
!    read and get all informations inside GSI diagnostic files.
!    .
!    .
!    .
!    .
!
!
!    +----------+------------+
!    | Variable |    Units   |
!    +----------+------------+
!    |    t     |     K      |
!    |    q     |   kg/kg    |
!    |    ps    |    hPa     |
!    |    uv    |    m/s     |
!    |    gps   |            |
!    |    sst   |     K      |
!    +----------+------------+
!    
!EOI
!---------------------------------------------------------------------
!BOP
!---------------------------------------------------------------------
! !ROUTINE: ReadDiagMod.f90
!---------------------------------------------------------------------
!               INPE/CPTEC Data Assimilation Group                   
!---------------------------------------------------------------------
!
! !REVISION HISTORY:
!  15 May 2012 - J. G. de Mattos - Initial Version
!  14 Aug 2017 - J. G. de Mattos - change to modular version
!  09 Oct 2017 - J. G. de Mattos - Include characteristics of OOP
!
!
!---------------------------------------------------------------------
!


module ReadDiagMod
  implicit none
  private
  
  public :: Diag
  public :: ObsInfo
  public :: ObsType
  public :: node

  !
  ! Parameters
  !
  
  integer, parameter  :: StrLen   = 512
  integer, parameter  :: i_kind   = selected_int_kind(8)
  integer, parameter  :: r_single = selected_real_kind(6)

  !
  ! Some parameters
  !
  Real,    Parameter :: udef  = 1.0e15 ! Undefined Value
  Logical, Parameter :: noiqc = .true. ! Logical Flag to OI QC (See GSI Manual)
  real,    parameter :: eps   = 10.0_r_single * tiny(0.0_r_single)
  !
  ! Levels to be Analyzed.
  ! These levels will be analyzed by layers
  !
  ! ex. 1000.00 - 1200.0
  !      900.00 -  999.9
  !        .         . 
  !        .         .
  !        .         .
  !        0.00 - 2000.0 this level will contain information about all levels
  !


  integer, parameter :: nlev = 14
  real, public, dimension(nlev), target :: default_levs = [       &
       1000.0,&
       900.0,&
       800.0,&
       700.0,&
       600.0,&
       500.0,&
       400.0,&
       300.0,&
       250.0,&
       200.0,&
       150.0,&
       100.0,&
       50.0,&
       0.0  &
       ]

  real, pointer :: levs(:) => null()

  !
  ! Diagnostic derived types
  !

  type :: Diag
     Private
     type(ObsInfo),   pointer       :: arq   => null()
     integer, public, pointer       :: nVars => null()
     integer, public, pointer       :: nObs  => null()
     logical                        :: impact
     real, public                   :: udef
     contains
        generic,   public  :: Open        => Open_, Open__
        procedure, private :: Open_, Open__
        procedure, public  :: Close       => Close_
        procedure, public  :: CalcStat    => CalcStat_
        procedure, public  :: PrintCount  => PrintCountStat_
        procedure, public  :: printObsInfo=> printObsInfo_
        procedure, public  :: GetTotalObs => GetTotalObs_
        procedure, public  :: GetNObs     => GetNObs_
        procedure, public  :: GetDate     => GetDate_
        procedure, public  :: GetObsInfo  => GetObsInfo_
        procedure, public  :: GetFirstVar => GetFirstVar_
        procedure, public  :: Gobt => GObt_
        procedure, public  :: testecount => testeCount__
  end type

  type :: ConvData
     character(len=8)    :: ID      ! stattion ID (Name or Number)
     character(len=4)    :: vname   ! Observation variable name
     real                :: kx      ! observation type
     real                :: lat     ! observation latitude (degrees)
     real                :: lon     ! observation longitude (degrees)
     real                :: lev     ! observation level reference
     real                :: elev    ! station elevation (meters)
     real                :: prs     ! observation pressure (hPa)
     real                :: dhgt    ! observation heigth (meters)
     real                :: time    ! obs time (minutes relative to analysis time)
     real                :: pbqc    ! input prepbufr qc or event mark
     real                :: iusev   ! analysis usage flag ( value )
     real                :: iuse    ! analysis usage flag (1=use, -1=monitoring )
     real                :: wpbqc   ! nonlinear qc relative weight
     real                :: inp_err ! prepbufr inverse obs error (unit**-1)
     real                :: adj_err ! read_prepbufr inverse obs error (unit**-1)
     real                :: end_err ! final inverse observation error (unit**-1)
     real                :: robs    ! observation
     real                :: omf     ! obs-ges used in analysis
     real                :: oma     ! obs-anl used in analysis
     real                :: error   ! final observation error (unit)
     real                :: imp     ! observation impact
     real                :: dfs     ! degrees of freedom for signal
     real                :: rmod    ! model
     !
     ! following variables are observation subtype dependent 
     ! So all are pointer
     real, pointer       :: qsges => null() ! guess saturation specific humidity (only for q)
     real, pointer       :: factw => null() ! 10m wind reduction factor (only for wind)
     real, pointer       :: pof   => null() ! data pof (kind of fligth - ascending, descending, only for aircraft)
     real, pointer       :: wvv   => null() ! data vertical velocoty (only for aircraft)
     real, pointer       :: tref  => null() ! sst Tr (adiative transfer model)
     real, pointer       :: dtw   => null() ! sst dt_warm at zob
     real, pointer       :: dtc   => null() ! sst dt_cool at zob
     real, pointer       :: tz    => null() ! sst d(tz)/d(tr) at zob 
  end type




  type :: ObsInfo
!     private
     character(len=3)        :: VarName     ! Name of Variable
     integer                 :: lim_qm      ! GSI/PreBufr quality control marker
     integer                 :: date        ! YYYYMMDDHH
     integer                 :: ymd         ! Year/month/Day
     integer                 :: hms         ! hour/minute/second
     integer                 :: nobs        ! total # of observation
     integer                 :: nkx         ! # of observation types (kx)
     logical                 :: stats = .false.
     logical                 :: impact= .false.
     integer, allocatable    :: use  (:)  ! total # of used observation
     integer, allocatable    :: nuse (:)  ! total # of unused observation
     integer, allocatable    :: rej  (:)  ! total # of rejeited observation by GSI Quality Control
     integer, allocatable    :: mon  (:)  ! total # of monitored observation
     real,    allocatable    :: vies (:)  ! bias
     real,    allocatable    :: rmse (:)  ! root mean square error
     real,    allocatable    :: mean (:)  ! mean 
     real,    allocatable    :: std  (:)
     real,    allocatable    :: imp  (:)  ! observation impact
     real,    allocatable    :: dfs  (:)  ! degree of freedom for signal

     type(ObsType), pointer  :: OT   => null() ! Incluindo esta separacao adicionou-se ~0.05s no processamento caso esteja em
                                               ! conjunto com a separacao inicial
     type(node),    pointer  :: head => null()
     type(node),    pointer  :: tail => null()
     type(ObsInfo), pointer  :: FirstVar => null()
     type(ObsInfo), pointer  :: NextVar => null()
  end type ObsInfo

  type :: ObsType
     real                   :: kx
     integer                :: nobs
     type(node),    pointer :: head => null()
     type(node),    pointer :: tail => null()

     type(ObsType), pointer :: FirstKX => null()
     type(ObsType), pointer :: NextKX => null()
  end type ObsType

!  type, private :: node
  type :: node
     type(ConvData)      :: data
     type(node), pointer :: next => null()
  end type node



!EOP
!--------------------------------------------------------------------!
contains
!--------------------------------------------------------------------!
!BOP
! 
! !FUNCTION: Open_()
!
! !DESCRIPTION: Função utilizada para abrir os arquivos diagnóticos
!               das observações convencionais do GSI e carregar
!               a informação na estrutura de dados ObsInfo
!
! !INTERFACE:
  function Open_(self, FileNameMask) result(iret)
     use m_string, only: str_template
     class(Diag)                     :: self
!
! !INPUT PARAMETERS:
!
     Character(len=*),          intent(in   ) :: FileNameMask ! Nome do arquivo a ser lido
                                                              ! use a palavra chave %e no nome 
                                                              ! do arquivo para ler diretamente
                                                              ! os diversos arquivos escritos
                                                              ! por cada processo MPI do GSI

!
! !OUTPUT PARAMETERS:
!
     Integer                         :: iret ! Código de erro
                                             !   0 : Sem erro
                                             !  -1 : File not found
                                             ! -99 : Erro na leitura
!EOP
!--------------------------------------------------------------------!
!EOC
     !
     ! local var
     !

     character(len=StrLen)  :: FileName
     type(ConvData)         :: conv
     type(ObsInfo), pointer :: info => null()
     type(ObsInfo), pointer :: tmp => null()

     integer :: ios
     integer :: ipe
     integer :: lu
     integer :: i
     character(len=3)                            :: var
     character(8),allocatable,dimension(:)       :: cdiagbuf
     real(r_single),allocatable,dimension(:,:)   :: rdiagbuf
     integer(i_kind)                             :: idate
     integer(i_kind)                             :: nchar,ninfo,nobs,mype

     logical                                     :: isNewVar
     logical                                     :: existe

     info => self%arq

     allocate(self%nVars)
     self%nVars = 0
     allocate(self%nObs)
     self%nObs = 0
     self%impact = .false.
     self%udef = udef
     
     lu  = 100
     ipe = 0
     FileName=trim(FileNameMask)
     inquire(File=trim(Filename), exist=existe)

!     if( ipe .eq. 0 .and. .not. existe)then
     if( .not. existe)then
        write(*,'(A,1x,A)')'File not found:',trim(FileName)
        iret = -1
        return
     endif

     OPEN ( UNIT   = lu,            &
            FILE   = trim(FileName),&
            STATUS = 'OLD',         &
            IOSTAT = ios,           &
            CONVERT= 'BIG_ENDIAN',  &
            ACCESS = 'SEQUENTIAL',  &
            FORM   = 'UNFORMATTED')
!     if(ios.ne.0) exit
     if(ios.ne.0) then
        print*,'error to open file',trim(FileName)
        iret = -1
        return
     endif

     if(ipe.eq.0) read(lu,err=997) idate

     GetVariables: do
        read(lu, err=998,end=110) var, nchar,ninfo,nobs,mype
        !+----------------------------------------------------
        !| list of data type used in GSI (kt list)
        !+----+-----------+
        !| kt |  Variable |
        !+----+-----------+
        !|  1 |    us
        !|  2 |    vs
        !|  3 |   slp 
        !|  4 |    u
        !|  5 |    v
        !|  6 |    h
        !|  7 |    w
        !|  8 |    t
        !|  9 |    td
        !| 10 |    rh
        !+----+------------------------------------------------
        if (nobs > 0) then

           allocate(cdiagbuf(nobs),rdiagbuf(ninfo,nobs))

           read(lu,err=999,end=109) cdiagbuf, rdiagbuf
        
           GetObs : do i=1,nobs

              conv%vname = trim(var)                ! observation variable name
!              conv%kt      =
              conv%kx      = nint(rdiagbuf(1,i))    ! observation type
              conv%lat     = rdiagbuf(3,i)          ! observation latitude (degrees)
              conv%lon     = rdiagbuf(4,i)          ! observation longitude (degrees)
              conv%elev    = rdiagbuf(5,i)          ! station elevation (meters)
              conv%prs     = rdiagbuf(6,i)          ! observation pressure (hPa)
              conv%dhgt    = rdiagbuf(7,i)          ! observation height (meters)
              conv%time    = rdiagbuf(8,i) * 60     ! obs time (minutes relative to analysis time)
              conv%pbqc    = rdiagbuf(9,i)          ! input prepbufr qc or event mark
              conv%iusev   = int(rdiagbuf(11,i))    ! read_prepbufr data usage flag
              conv%iuse    = int(rdiagbuf(12,i))    ! analysis usage flag (1=use, -1=monitoring/not used)
              conv%wpbqc   = rdiagbuf(13,i)         ! nonlinear qc relative weight
              conv%inp_err = rdiagbuf(14,i)         ! prepbufr inverse obs error (unit**-1)
              conv%adj_err = rdiagbuf(15,i)         ! read_prepbufr inverse obs error (unit**-1)
              conv%end_err = rdiagbuf(16,i)         ! final inverse observation error (unit**-1)
              if ( rdiagbuf(16,i) .gt. eps )then
                 conv%error = 1.0/rdiagbuf(16,i)  ! final observation error (unit**-1)
              else
                 conv%error = udef
              endif
              conv%robs    = rdiagbuf(17,i)         ! observation
              conv%omf     = rdiagbuf(18,i)         ! obs-ges used in analysis (K)
              conv%rmod    = conv%robs-conv%omf
              
              ! will be assingn if are read two files (see function Open__)
              conv%imp     = udef
              conv%dfs     = udef
              conv%oma     = udef
              !
              ! Some adjustments
              !
              
              ! GPS data
              if (trim(var) .eq. 'gps')then
                 conv%pbqc  = rdiagbuf(10,i)       ! input prepbufr qc or event mark
                 conv%omf   = rdiagbuf(17,i)  *  rdiagbuf(5,i)
                 conv%oma   = udef
                 conv%rmod  = conv%robs-conv%omf
                 ! pbqc
                 !   * one => ! Remove observation if below surface or at/above the top layer 
                              ! of the model by setting observation (1/error) to zero.
                              ! Make no adjustment if observation falls within vertical
                              ! domain.
                 !   * two => Remove obs above 30 km in order to avoid increments at top model
                 !   * three => fail in gross check
                 !   * Four => ! - Remove MetOP/GRAS data below 8 km
                 !             ! - cutoff
              endif

              ! When the data is q, unit convert kg/kg -> g/kg **/

              if (trim(var) .eq. '  q') then
                 conv%robs     = conv%robs * 1000.0
                 conv%rmod     = conv%rmod * 1000.0
                 conv%omf      = conv%omf * 1000.0
                 conv%inp_err  = conv%inp_err * 1000.0
                 conv%adj_err  = conv%adj_err * 1000.0
                 conv%end_err  = conv%end_err * 1000.0
                 conv%error    = conv%error * 1000.0
                 allocate(conv%qsges)
                 conv%qsges    = rdiagbuf(20,i) * 1000.0 ! guess saturation specific humidity
              end if

              ! When the data is pw, replase the rprs to udef                 
              if (var .eq. ' pw') conv%time = udef

              ! When the data is return spd
              if ( var .eq. ' uv')then

                 ! Wind at gsi diag is speed = sqrt(u**2+v**2)
                 allocate(conv%factw)
                 conv%factw = rdiagbuf(20,i) ! 10m wind reduction factor

              endif
              
              ! if aircraft information
              if (var .eq. '  t' .and. ninfo .ge. 20)then
                 allocate(conv%pof)
                 conv%pof = rdiagbuf(20,i) ! data pof
                                           !    pof = 5 (ascending)
                                           !    pof = 6 (descending)
                                           !    pof = 3 (cruise level)
                 allocate(conv%wvv)
                 conv%wvv = rdiagbuf(21,i) ! data vertical velocity
              else
                 allocate(conv%pof)
                 conv%pof = udef
                 allocate(conv%wvv)
                 conv%wvv = udef
              endif

              if (var .eq. 'sst' .and. ninfo .ge. 21)then
                 allocate(conv%tref)
                 conv%tref = rdiagbuf(21,i) ! sst Tr (adiative transfer model)

                 allocate(conv%dtw)
                 conv%dtw  = rdiagbuf(22,i) ! sst dt_warm at zob

                 allocate(conv%dtc)
                 conv%dtc  = rdiagbuf(23,i) ! sst dt_cool at zob

                 allocate(conv%tz)
                 conv%tz   = rdiagbuf(24,i) ! sst d(tz)/d(tr) at zob
              else
                 allocate(conv%tref)
                 conv%tref = udef
                 allocate(conv%dtw)
                 conv%dtw  = udef
                 allocate(conv%dtc)
                 conv%dtc  = udef
                 allocate(conv%tz)
                 conv%tz   = udef
              endif

              if(conv%robs .gt. 1.0e8) then
                 conv%robs = udef
                 conv%omf  = udef 
              endif

              !
              ! insert data to conv structure
              !

              call insert(info, trim(var), conv, isNewVar, idate)


              if ( isNewVar ) self%nVars = self%nVars + 1

           enddo GetObs

109        continue
           deallocate(cdiagbuf,rdiagbuf)
        else
           read(lu)           
        endif
        
     enddo GetVariables
110  continue     
     close(lu)

!     call SortOtype(info)

     !
     ! count total number of observations
     tmp => info%FirstVar
     do i = 1, self%nVars
        self%nObs = self%nObs + tmp%nobs
        tmp=>tmp%nextVar
     enddo

     ! put observation info on global variable
     self%arq => info%FirstVar
     !print*,trim(fileNameMask)
     iret=self%PrintObsInfo()


     iret = 0
     return

997  iret = -95
     return

998  iret = -96
     return

999  iret = -97
     return

  end function

  function Open__(self, File_FGS, File_ANL) result(iret)
     class(Diag)                     :: self
     character(len=*), intent(in   ) :: File_FGS
     character(len=*), intent(in   ) :: File_ANL
     Integer                         :: iret


     type(Diag)  :: file1, file2
     type(ObsInfo), pointer  :: info1 => null()
     type(ObsInfo), pointer  :: info2 => null()
     type(ObsType), pointer  :: OT1 => null()
     type(ObsType), pointer  :: OT2 => null()
     type(node),    pointer  :: kx1 => null()
     type(node),    pointer  :: kx2 => null()

     real, pointer :: oma => null()
     real, pointer :: omf => null()
     real, pointer :: err => null()

     integer    :: ierr

     iret = 0     

     ierr = file1%open(File_FGS)
     if(ierr.ne.0)then
        print*,'error on file1:',trim(File_FGS), ierr
        iret = ierr
        return
     endif


     ierr = file2%open(File_ANL)
     if(ierr.ne.0)then
        print*,'error on file2:',trim(File_ANL), ierr
        iret = ierr
        return
     endif

     ! assingn Ges and Anl and obtain impact
     if (file1%nObs .ne. file2%nObs)then
        write(*,'(1x,A,1x,2I10)')'Dimension mismatch : <file1,file2>',file1%nObs,file2%nObs
        write(*,'(1x,A)')'Files must match! Will exit ....'
        call exit
     endif


     info1 => file1%arq%FirstVar
     info2 => file2%arq%FirstVar

     info1%impact = .true. 
     self%impact = .true.
     
     do while(associated(info1))
        OT1 => info1%OT%FirstKX
        OT2 => info2%OT%FirstKX
        do while(associated(OT1))
           kx1 => OT1%head
           kx2 => OT2%head
           do while(associated(kx1))
              kx1%data%oma   = kx2%data%omf
              kx1%data%error = kx2%data%error

              omf => kx1%data%omf
              oma => kx1%data%oma
              err => kx1%data%error

              if(err .gt. eps .and. err .lt. 10.0)then
                 kx1%data%imp   = (oma**2 - omf**2) / err
                 kx1%data%dfs   = ( ( oma - omf ) * (omf ) ) / err
              else
                 kx1%data%imp = udef
                 kx1%data%dfs = udef
              endif


              kx1 => kx1%next
              kx2 => kx2%next
           enddo
           OT1 => OT1%nextKX
           OT2 => OT2%nextKX
        enddo
        info1 => info1%nextVar
        info2 => info2%nextVar
     enddo

     self%arq => file1%arq
     self%nVars => file1%nVars
     self%nObs => file1%nObs

     ierr = file2%close( )

  end function

  function close_(self) result(iret)
     class(Diag) :: self
     integer     :: iret

     type(ObsInfo), pointer :: Obs => null()
     type(ObsType), pointer :: kx => null()
     type(node),    pointer :: ObsData => null()

     iret = 0

     Obs => self%arq%FirstVar%NextVar
     do

        kx => self%arq%FirstVar%OT%nextKX
        do

           ObsData => self%arq%FirstVar%OT%head%next
           do
              deallocate(self%arq%FirstVar%OT%head)
              if(.not.associated(ObsData)) exit
              self%arq%FirstVar%OT%head => ObsData
              ObsData => ObsData%next
           enddo

           deallocate(self%arq%FirstVar%OT)
           if(.not.associated(kx)) exit
           self%arq%FirstVar%OT => kx
           kx => self%arq%FirstVar%OT%nextKX

        enddo

        deallocate(self%arq%FirstVar)
        if(.not.associated(Obs)) exit
        self%arq%FirstVar => Obs
        Obs => self%arq%FirstVar%NextVar
     enddo

  end function

  subroutine init_(self, VarName, idate, data)

     type(ObsInfo), pointer, intent(inout) :: self
     character(len=*),       intent(in   ) :: VarName
     integer,                intent(in   ) :: idate ! synoptic year/month/day
     type(ConvData),         intent(in   ) :: data

     type(ObsType), pointer :: OT => null()

     integer :: iret, istat

     istat = 0
     allocate(self, stat = iret)
     istat = istat + iret

!     allocate(self%head, stat = iret)
!     istat = istat + iret

!     nullify(self%head%next)
     
     self%VarName   = trim(VarName)
     self%nobs      = 1
     self%date      = idate
     self%ymd       = int(idate/100)
     self%hms       = mod(idate,100) * 10000
!     self%head%data = data
!     self%tail      => self%head

     call def_limqm(self)

     !
     ! insert data by ObsType
     !

     allocate(self%OT, stat=iret)
     istat = istat + iret
     OT    => self%OT

     allocate(OT%head, stat=iret)
     istat = istat + iret 

     nullify(OT%head%next)

     OT%kx        = data%kx
     OT%nobs      = 1
     self%nkx     = 1

     OT%head%data = data
     OT%tail      => OT%head
     OT%FirstKX   => OT
     nullify(OT%nextKX)

     if (istat .ne. 0 ) then 
        print*,'Problem to init ...'
        stop
     endif
     return
  end subroutine

  function IsEmpty(self) result(answer)
     type(ObsInfo), pointer, intent(in) :: self
     logical :: answer
     
     answer = .not.associated(self)

  end function

  recursive subroutine insert(self,  VarName, data, isNewVar, idate)

    type(ObsInfo), pointer, intent(inout) :: self
    character(len=*),       intent(in   ) :: VarName
    type(ConvData),         intent(in   ) :: data
    logical, optional,      intent(  out) :: isNewVar
    integer, optional,      intent(in   ) :: idate ! synoptic year/month/day

    integer                :: date

    type(ObsInfo), pointer :: NewVar => null()
    type(ObsInfo), pointer :: Find => null()
    type(ObsInfo), pointer :: FirstVar => null()
    type(ObsType), pointer :: OT => null()

    integer :: iret

    if(present(isNewVar)) isNewVar = .FALSE.

    if(present(idate))then
       date = idate
    else
       date = 0
    endif
    !
    ! Verify if self is null
    !
    
    if(IsEmpty(self)) then

       !
       ! Only at First time
       !

       call init_(                        &
                  self    = self,         &
                  VarName = trim(VarName),&
                  idate   = date,         &          
                  data    = data          &
                 )

       self%FirstVar => self
       nullify(self%NextVar)

       if(present(isNewVar)) isNewVar = .TRUE.

       return

    endif

    if(trim(self%Varname).eq.trim(VarName))then
       !
       ! Insert a new observation point
       ! in an existing variable
       !
!       allocate(NewNode)
!       nullify(NewNode%next)

!       NewNode%data = data
       self%nobs = self%nobs + 1
    
!       self%tail%next => NewNode
!       self%tail => self%tail%next

       !
       ! Organize data by Observation Type
       !

       ! verify if current pointer have same kx
       ! and associate with the data
       if(self%OT%kx .eq. data%kx)then

          allocate(self%OT%tail%next)
          self%OT%tail%next%data = data
          self%OT%tail           => self%OT%tail%next

          self%OT%nobs           = self%OT%nobs + 1
          
       else

          ! find by required kx
          OT => self%OT%FirstKX
          do while(associated(OT))
            if(data%kx .eq. OT%kx)exit
            self%OT => OT
            OT      => OT%NextKX
          enddo
   
          if(associated(OT))then

             allocate(OT%tail%next)
             OT%tail%next%data = data
             OT%tail           => OT%tail%next

             OT%nobs           = OT%nobs + 1

          else
   
             allocate(OT, stat=iret)
             allocate(OT%head)
             nullify(OT%head%next)
   
             OT%kx        = data%kx
             OT%nobs      = 1
             OT%head%data = data
             OT%tail      => OT%head
             OT%FirstKX   => self%OT%FirstKX
   
             self%OT%nextKX => OT
             self%OT        => self%OT%NextKX
             self%nkx       = self%nkx + 1
          endif
       endif

     else ! Insert a new variable

        !
        ! Return to first variable
        !

        Find => self%FirstVar
        FirstVar => self%FirstVar

        !
        ! Find by variable name
        ! in list

        do while(associated(Find))
           if(trim(Find%VarName) .eq. trim(VarName))then
              call insert(Find, VarName, data)
              self => Find
              return
           endif
           self => Find
           Find => Find%NextVar
        enddo

        !
        ! if not found
        ! create a NewVariable
        !

        allocate(NewVar)
        nullify(NewVar%NextVar)
        call init_(                        &
                   self    = NewVar,       &
                   VarName = trim(VarName),&
                   idate   = date,         &
                   data    = data          &
                  )

        NewVar%FirstVar => FirstVar
        self%NextVar    => NewVar
        self => self%NextVar

        if(present(isNewVar)) isNewVar = .TRUE.

     endif


    return
  end subroutine insert

  function CalcStat_(self, levels) result(iret)
     class(Diag),              intent(in   ) :: self
     real, optional,  pointer, intent(in   ) :: levels(:)


     real, pointer          :: zlevs (:)
     type(ObsInfo), pointer :: Now
     integer                :: iret


     if(present(levels))then
        zlevs => levels
     else
        zlevs => default_levs
     endif
     Now => self%arq%FirstVar
     do while(associated(Now))

        call StatCount_(Now, zlevs)

        Now => Now%NextVar
     enddo

     iret = 0

     return

  end function

!  ! Sorting by OT
!  subroutine SortOtype( self )
!     type(ObsInfo), pointer, intent(inout) :: self
!
!     type(ObsInfo), pointer :: Var => null()
!
!     Var => self%FirstVar
!     do while(associated(Var))
!        Var%OT%FirstKX  => MergeSort(Var%OT%FirstKX)
!        Var => Var%NextVar
!     enddo
!     
!  end subroutine
!
!
!--------------------------------------------------------------------!
!BOP
!
! !IROUTINE: splitList
!
! !DESCRIPTION: Split the nodes of the given list into front and back halves,
!               and return the two lists using the reference parameters.
!               If the length is odd, the extra node should go in the front list.
!               Uses the fast/slow pointer strategy.
!
! !INTERFACE:
!
   subroutine splitList(source, frontRef, backRef)
!
! !INPUT PARAMETERS:
!
      type(ObsType), pointer, intent(in   ) :: source
!
! !OUTPUT PARAMETERS:
!
      type(ObsType), pointer, intent(  out) :: frontRef => null()
      type(ObsType), pointer, intent(  out) :: backRef => null()
!
! !REVISION HISTORY: 
!
!
!EOP
!--------------------------------------------------------------------!
!BOC
      type(ObsType), pointer :: slow => null()
      type(ObsType), pointer :: fast => null()


      slow => source
      fast => source%nextKX

      ! Advance 'fast' two nodes, and advance 'slow' one node
      do while (associated(fast))
         fast => fast%nextKX
         if(associated(fast))then
            slow => slow%nextKX
            fast => fast%nextKX
         endif
      enddo

      ! 'slow' is before the midpoint in the list, so split it in two 
      !  at that point.

      frontRef => source
      backRef => slow%nextKX
      slow%nextKX => null()
      
      return

   end subroutine
!EOC
!--------------------------------------------------------------------!
!BOP
!
! !IROUTINE: SortedMerge
!
! !DESCRIPTION: Takes two linked lists and merges the two together
!               into one linked list which is in increasing order.
!
! !INTERFACE:
!
   recursive function SortedMerge(a,b) result(lista)
!
! !INPUT PARAMETERS:
!
      type(ObsType), pointer :: a
      type(ObsType), pointer :: b
!
! !OUTPUT PARAMETERS:
!
      type(ObsType), pointer :: lista
!
! !REVISION HISTORY: 
!
! !NOTA:
!
!  See https://www.geeksforgeeks.org/?p=3622 for details of this  
!  function.
!  Here we use Method 3 (Recursion method)
!
!EOP
!--------------------------------------------------------------------!
!BOC

      nullify(lista)

      if(.not.associated(a))then
         lista => b
         return
      else if(.not.associated(b))then
         lista => a
         return
      endif

      if(a%kx <= b%kx)then
         lista => a
         lista%nextKX => SortedMerge(a%nextKX,b)
      else
         lista => b
         lista%nextKX => SortedMerge(a,b%nextKX)
      endif

      return     

   end function
!EOC
!--------------------------------------------------------------------!
!BOP
!
! !IROUTINE: MergeSort
!
! !DESCRIPTION: sorts the linked list by changing next pointers (not data)
!
! !INTERFACE:
!
   recursive function MergeSort(headRef) result(lista)
!
! !INPUT PARAMETERS:
!
      type(ObsType), pointer :: headRef
!
! !OUTPUT PARAMETERS:
!
      type(ObsType), pointer :: lista
! !REVISION HISTORY: 
!
! !NOTA:
!
!EOP
!--------------------------------------------------------------------!
!BOC

      type(ObsType), pointer :: a
      type(ObsType), pointer :: b
      type(ObsType), pointer :: head

      ! Base case -- length 0 or 1
      if(.not.associated(headRef) .or. .not.associated(headRef%nextKX))then
         lista => headRef
         return
      endif

      head => headRef
      do while(associated(head))
         head => head%nextKX
      enddo

      head => headRef
      
      ! Split head into 'a' and 'b' sublists
      call splitList(head,a,b)

      ! Recursively sort the sublists
      a => MergeSort(a)
      b => MergeSort(b)

      ! answer = merge the two sorted lists together
      lista => SortedMerge(a,b)

   end function

!EOC
!--------------------------------------------------------------------!


  !-------------------------------------------------------------------!
  !BOP
  subroutine StatCount_(self, zlevs)

  !
  ! !INPUT PARAMETERS:
  !
     type(ObsInfo), pointer, intent(inout) :: self
     real,          pointer, intent(in   ) :: zlevs(:)

  !EOP
  !-------------------------------------------------------------------!
  !BOC
     type(ObsType), pointer :: OT =>null()
     type(node),    pointer :: Obs =>null()
     
     integer :: nzp
     integer :: k
     logical :: flag1, flag2, flag3

     self%stats = .true.
     OT => self%OT%FirstKX

     nzp = size(zlevs)

     allocate(self%use(0:nzp))
     allocate(self%nuse(0:nzp))
     allocate(self%rej(0:nzp))
     allocate(self%mon(0:nzp))
     allocate(self%imp(0:nzp))
     allocate(self%dfs(0:nzp))

     self%use  = 0
     self%nuse = 0
     self%rej  = 0
     self%mon  = 0 
     
     self%imp  = 0
     self%dfs  = 0

!    if(associated(obs)) print*,'Associated OBS'
     do while(associated(OT))
     
        Obs => OT%head
        do while(associated(Obs))
           ! Get observation level

           k = minloc(Obs%data%prs-zlevs,mask=(Obs%data%prs-zlevs).ge.0,DIM=1)

           !
           ! Counting number of observations accepted, reject and monitored
           !

           if (Obs%data%iuse.eq. 1) self%use(k)  = self%use(k)  + 1
           if (Obs%data%iuse.eq.-1) self%nuse(k) = self%nuse(k) + 1

           !
           !   The QC process creates a number indicating the data quality for each observation.
           ! These numbers are called QC markers in PrepBUFR files and are important as parts of
           ! the observation information. GSI uses QC markers to decide how to use the data. A 
           ! brief summary of the meaning of the QC markers is as follows:
           ! 
           !    +-----------------+-----------------------------------------------------------+
           !    | QC markes range | Data Process in GSI                                       |
           !    +-----------------+-----------------------------------------------------------+
           !    |  > 15 or        |GSI skips these observations during reading procedure. That|
           !    |  <= 0           |means these observations are tossed                        | 
           !    +-----------------+-----------------------------------------------------------+
           !    |  >= lim_qm      |These observations will be in monitoring status. That means|
           !    |  and            |these observations will be read in and be processed through|
           !    |  < = 15         |GSI QC process (gross check) and innovation calculation    | 
           !    |                 |stage but will not be used in inner iteration.             |
           !    +-----------------+-----------------------------------------------------------+
           !    |  > 0            |Observations will be used in further gross check (failure  |
           !    |  and            |observation will be list in rejection), innovation         |
           !    |  < lim_qm       |caalculation, and the analysis (inner iteration).          |
           !    +-----------------+-----------------------------------------------------------+
           !

           if (Obs%data%iuse.eq.-1 )then

              flag1 = ( Obs%data%pbqc > 15.0  .or. Obs%data%pbqc <=  0.0 )
              flag2 = ( Obs%data%pbqc >= self%lim_qm .and. Obs%data%pbqc <=15 )
              flag3 = ( Obs%data%pbqc >  0.0 .and. Obs%data%pbqc <  self%lim_qm )

              if( flag1 .or. flag3 )then
                 self%rej(k) = self%rej(k) + 1
              elseif(flag2)then
                 self%mon(k) = self%mon(k) + 1
              endif

            endif

!            ! Account observation impact ??!!
            if ( ( Obs%data%iuse .ge. 1 ) .and. (Obs%data%imp .ne. udef) )then
               self%imp(k) = self%imp(k) + Obs%data%imp
               self%dfs(k) = self%dfs(k) + Obs%data%dfs
            endif

            Obs => Obs%next
         enddo

         OT => OT%NextKX
     enddo



     self%use(0)  = sum(self%use)
     self%nuse(0) = sum(self%nuse)
     self%rej(0)  = sum(self%rej)
     self%mon(0)  = sum(self%mon)
     self%imp(0)  = sum(self%imp)
     self%dfs(0)  = sum(self%dfs)

     ! make fractional observation impacts
     do k=1, size(zlevs)
        if (self%imp(0) .ne. 0)self%imp(k)  = self%imp(k)  / self%imp(0)
        if (self%dfs(0) .ne. 0)self%dfs(k)  = self%dfs(k)  / self%dfs(0)
     enddo


     return
  end subroutine

  !EOC
  !-------------------------------------------------------------------!


  !-------------------------------------------------------------------!
  !BOP
  !
  ! !IROUTINE: def_limqm()
  !
  ! !DESCRIPTION: This function set limqm for each variable
  !               limqm is used to control what data will be
  !               acept or not by GSI quality control.
  !               The parameter lim_qm is a threshold set in GSI read 
  !               in procedure. The current values of lim_qm in GSI are
  !               listed in the following table:
  !
  !        +----------------------+---------------+---------------+
  !        |The value of namelist | lim_qm for Ps | lim_qm others |
  !        |option noiqc          |               |               |
  !        +----------------------+---------------+---------------+
  !        |True (without OI QC)  |       7       |       8       |
  !        +----------------------+---------------+---------------+
  !        |False (with OI QC)    |       4       |       4       |
  !        +----------------------+---------------+---------------+
  !
  ! !INTERFACE
  !
  subroutine def_limqm(self)

  !
  ! !INPUT/OUTPUT PARAMETERS:
  !
     type(ObsInfo), pointer, intent(inout) :: self ! data structure
  !
  !
  ! !REVISION HISTORY: 
  !  129 Jun 2017 - J. G. de Mattos - Initial Version
  !
  !
  !EOP
  !-------------------------------------------------------------------!
  !BOC
  !

     if(noiqc)then
        self%lim_qm = 8
        if(trim(self%VarName).eq.' ps') self%lim_qm = 7
     else
        self%lim_qm = 4
     endif

  end subroutine
  !
  !EOC
  !-------------------------------------------------------------------!


  function GetTotalObs_(self)result(nobs)
     class(Diag)          :: self
     integer             :: nobs

     type(ObsInfo), pointer  :: tmp => null()


     nobs = 0
     tmp => self%arq%FirstVar
     do while(associated(tmp))
        nobs = nobs + tmp%nobs
        tmp => tmp%NextVar
     enddo

  end function

   function GObt_(self,ObsName) result(iret)
     class(diag)      :: self
     character(len=*) :: obsName
     integer          :: iret
     type(ObsInfo), pointer  :: tmp => null()
     type(ObsType), pointer  :: OT => null()
     character(len=10) :: v1, v2

     v1 = trim(adjustl(ObsName))

     tmp => self%arq%FirstVar
     do while(associated(tmp))
        v2 = trim(adjustl(tmp%VarName))

        if(v1 .eq. v2)then
           !print*,'NObsType: ',tmp%nkx, tmp%nobs
           OT => tmp%OT%FirstKX
           do while(associated(OT))
              !print*, trim(v1), OT%kx, OT%nobs
              OT => OT%nextKX
           enddo
        endif

        tmp => tmp%NextVar
     enddo

     iret = 0


  end function

  function GetDate_(self) result (idate)
     class(diag)   :: self
     integer       :: idate

     idate = self%arq%date
     
  endfunction


  function GetNObs_(self,ObsName)result(nobs)
     class(Diag)         :: self
     character(len=*)    :: ObsName
     integer             :: nobs

     type(ObsInfo), pointer  :: tmp => null()
     character(len=10) :: v1, v2

     v1 = trim(adjustl(ObsName))

     nobs = 0
     tmp => self%arq%FirstVar
     do while(associated(tmp))
        v2 = trim(adjustl(tmp%VarName))

        if(v1 .eq. v2) nobs = nobs + tmp%nobs

        tmp => tmp%NextVar
     enddo

  end function

  subroutine GetFirstVar_(self, FirstVar)
     class(diag)            :: self
     type(ObsInfo), pointer, intent(out) :: FirstVar => null()

     FirstVar => self%arq%FirstVar

  end subroutine



  function GetObsInfo_(self, ObsName, KX, zlevs)result(ObsTable)
     class(Diag)         :: self
     character(len=*)    :: ObsName
     integer             :: KX
     real, optional      :: zlevs(:)
     real, allocatable   :: ObsTable(:,:)
     integer :: istat
     integer :: k


     type(ObsInfo), pointer  :: var => null()
     type(ObsType), pointer  :: OT  => null()
     type(node),    pointer  :: obs  => null()
     integer ::  i

     character(len=10) :: v1, v2


     !------------------------------------------!
     ! Set were are the standard atmospheric levels 
     !
     if(present(zlevs))then
        allocate(levs(size(zlevs)))
        levs = zlevs
     else
        levs => default_levs
     endif
     !
     !------------------------------------------!


     v1 = trim(adjustl(ObsName))
     
     var => self%arq%FirstVar
     FindVar : do while(associated(var))

        v2 = trim(adjustl(var%VarName))

        if ( v1 .eq. v2 )then

           OT => var%OT%FirstKX

           do while(associated(OT))

              if(OT%kx .eq. KX)then

                 obs  => OT%head

                 if (allocated(ObsTable)) deallocate(ObsTable)
            
                 !select case (trim(ObsName))
                 !   case ('  q')
                 !      allocate(ObsTable(OT%nObs,21), stat = istat)
                 !   case (' uv')
                 !      allocate(ObsTable(OT%nObs,21), stat = istat)
                 !   case('  t')
                 !      allocate(ObsTable(OT%nObs,22), stat = istat)
                 !   case('sst')
                 !      allocate(ObsTable(OT%nObs,24), stat = istat)
                 !   case default
                 !      allocate(ObsTable(OT%nObs,20), stat = istat)
                 !end select
                 if(self%impact)then
                    allocate(ObsTable(OT%nObs,19), stat = istat)
                 else
                    allocate(ObsTable(OT%nObs,16), stat = istat)
                 endif
                 if(istat .gt. 0) return
            
                 do i = 1, OT%nObs

                    k = minloc(obs%data%prs-levs,mask=(obs%data%prs-levs).ge.0,DIM=1)
            
                    ObsTable(i, 1) = Obs%data%lat     ! observation latitude (degrees)
                    ObsTable(i, 2) = Obs%data%lon     ! observation longitude (degrees)
                    ObsTable(i, 3) = Obs%data%elev    ! station elevation (meters)
                    ObsTable(i, 4) = Obs%data%prs     ! observation pressure (hPa)
                    ObsTable(i, 5) = Obs%data%dhgt    ! observation height (meters)
                    ObsTable(i, 6) = levs(k)          ! observation reference level (hPa)
                    ObsTable(i, 7) = Obs%data%time    ! obs time (minutes relative to analysis time)
                    ObsTable(i, 8) = Obs%data%pbqc    ! input prepbufr qc or event mark
                    ObsTable(i, 9) = Obs%data%iuse    ! analysis usage flag (1=use, -1=monitoring )
                    ObsTable(i,10) = Obs%data%iusev   ! analysis usage flag ( value )
                    ObsTable(i,11) = Obs%data%wpbqc   ! nonlinear qc relative weight
                    ObsTable(i,12) = Obs%data%inp_err ! prepbufr inverse obs error (unit**-1)
                    ObsTable(i,13) = Obs%data%adj_err ! read_prepbufr inverse obs error (unit**-1)
                    ObsTable(i,14) = Obs%data%end_err ! final inverse observation error (unit**-1)
                    ObsTable(i,15) = Obs%data%robs    ! observation
                    ObsTable(i,16) = Obs%data%omf     ! obs-ges used in analysis (K)
                    if (self%impact)then
                       ObsTable(i,17) = Obs%data%oma     ! obs-anl used in analysis (K)
                       ObsTable(i,18) = Obs%data%imp     ! observation impact
                       ObsTable(i,19) = Obs%data%dfs     ! degree of freedom for signal
                    endif
                   ! ObsTable(i,20) = Obs%data%kx
            
                   ! select case(trim(ObsName))
                   !    case('  q')
                   !       ObsTable(i,21) = Obs%data%qsges ! guess saturation specific humidity
                   !    case(' uv')
                   !       ObsTable(i,21) = Obs%data%factw ! 10m wind reduction factor
                   !    case('  t')
                   !       ObsTable(i,21) = Obs%data%pof ! data pof
                   !       ObsTable(i,22) = Obs%data%wvv ! data vertical velocity
                   !    case('sst')
                   !       ObsTable(i,21) = Obs%data%tref ! sst Tr (adiative transfer model)
                   !       ObsTable(i,22) = Obs%data%dtw  ! sst dt_warm at zob
                   !       ObsTable(i,23) = Obs%data%dtc  ! sst dt_cool at zob
                   !       ObsTable(i,24) = Obs%data%tz   ! sst d(tz)/d(tr) at zob
                   ! end select
            
                    Obs => Obs%next

                 enddo

                 exit FindVar

              endif

              OT => OT%NextKX
           enddo
        endif

        var => var%NextVar
     enddo FindVar

     if(present(zlevs))deallocate(levs)
     
!     Obs => root%next
!     do 
!        deallocate (root)
!        if(.not.associated(Obs)) exit
!        root => Obs
!        Obs => Obs%next
!     enddo

     istat = 0

  end function


  function PrintCountStat_(self, zlevs) result(iret)
     class(diag)             :: self
     real, optional          :: zlevs(:)
     type(ObsInfo), pointer  :: tmp => null()
     integer :: iret
     integer :: i
     integer :: sumobs
     
      !------------------------------------------!
      ! Set were are the standard atmospheric levels 
      !
      if(present(zlevs))then
         allocate(levs(size(zlevs)))
         levs = zlevs
      else
         levs => default_levs
      endif
      !
      !------------------------------------------!

     tmp => self%arq%FirstVar
     sumobs=0
     do while(associated(tmp))
        write(*,'(2x,2A)')'Variable Name:',trim(tmp%VarName)
        write(*,'(4x,A,I6.1)')'├── Total of Observations:', tmp%nobs
        if(tmp%stats)then
           i=0
           write(*,'(4x,A,5x,4(A10),2(A16))')'└── Level','Used','Not Used','Rejeited','Monitored','Impact','DFS'
           write(*,'(12x,A6,4I10.1,2F16.3)')'Total ──',tmp%use(i),tmp%nuse(i), tmp%rej(i), tmp%mon(i), &
           tmp%imp(i), tmp%dfs(i)
           do i=1,nlev
              if(i.lt.nlev)then
                 write(*,'(9x,A,F6.1,4I10.1,2F16.3)')'├──',levs(i),tmp%use(i),tmp%nuse(i), tmp%rej(i), tmp%mon(i),&
                 tmp%imp(i), tmp%dfs(i)
              else
                 write(*,'(9x,A,F6.1,4I10.1,2F16.3)')'└──',levs(i),tmp%use(i),tmp%nuse(i), tmp%rej(i), tmp%mon(i), &
                 tmp%imp(i), tmp%dfs(i)
              endif
           enddo
        endif
        sumobs = sumobs + tmp%nobs
        tmp => tmp%NextVar
     enddo
     write(*,*)''
     write(*,'(9x,A,I10)')'Total number of observations analyzed:', sumobs
     write(*,*)''
     if(present(zlevs))deallocate(levs)

     iret = 0

  endfunction

  function printObsInfo_(self)result(iret)
     class(diag) :: self
     integer:: iret
     type(ObsInfo), pointer  :: tmp => null()
     type(ObsType), pointer  :: ot => null()

     iret = 0
     tmp => self%arq%FirstVar
     do while(associated(tmp))
        ot => tmp%OT%FirstKx
        !print*,'--->',trim(tmp%varName)
        do while(associated(ot))
          !print*,'        - ',ot%kx
          ot => ot%nextKx
        enddo
        tmp => tmp%nextVar
     enddo

  end function

  function testeCount__(self) result(iret)
     class(Diag),              intent(in   ) :: self
     type(ObsInfo), pointer :: Now => null()
     type(ObsType), pointer :: Obs =>null()
     type(node),    pointer :: dat => null()

     integer :: Total, Total00, Total01
     integer :: iret

     iret = 0

     Total   = 0
     Total01 = 0
     Now => self%arq%FirstVar
     do while(associated(Now))
        Total   = Total + Now%nObs

        Total00 = 0
        Obs => Now%OT%FirstKX
        do while(associated(Obs))
           dat => Obs%head
           do while(associated(dat))

           Total00 = Total00 + 1
              dat=>dat%next
           enddo
           Obs => Obs%nextKX
        enddo
        Total01 = Total01 + Total00


        Now => Now%NextVar
     enddo

     print*, total, total01

  end function

 end module ReadDiagMod
